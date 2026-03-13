from __future__ import annotations

import base64
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass

import jwt
import requests

EXCLUDED_PATTERNS = [
    # ── Dependency directories ─────────────────────────────────────────────
    "node_modules/",
    "vendor/",
    "venv/",
    ".venv/",
    "env/",
    ".env/",
    "__pycache__/",
    ".cache/",
    ".tmp/",
    # ── Build & dist artifacts ─────────────────────────────────────────────
    ".next/",
    "dist/",
    "build/",
    "out/",
    "target/",
    "_site/",
    ".nuxt/",
    ".output/",
    # ── Lock files (noisy, no architectural value) ─────────────────────────
    "yarn.lock",
    "pnpm-lock.yaml",
    "package-lock.json",
    "poetry.lock",
    "uv.lock",
    "composer.lock",
    "gemfile.lock",
    "cargo.lock",
    ".terraform.lock.hcl",
    "go.sum",
    "pdm.lock",
    # ── Compiled / binary / media files ───────────────────────────────────
    ".min.",
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".class",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".ico",
    ".svg",
    ".ttf",
    ".woff",
    ".woff2",
    ".webp",
    ".mp4",
    ".mp3",
    ".wav",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    # ── Sensitive / secret files ────────────────────────────────────────────
    # (these should never be in a repo, but belt-and-suspenders)
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    ".pem",
    ".p12",
    ".pfx",
    ".cer",
    "service-account.json",
    "secrets/",
    "secret/",
    # ── IDE / OS noise ─────────────────────────────────────────────────────
    ".vscode/",
    ".idea/",
    ".DS_Store",
    "thumbs.db",
    "*.log",
    # ── Coverage / snapshot artifacts ─────────────────────────────────────
    ".coverage",
    "htmlcov/",
    "coverage/",
    "__snapshots__/",
]


@dataclass(frozen=True)
class GithubData:
    default_branch: str
    file_tree: str
    readme: str
    tech_context: str


def detect_tech_context(file_paths: list[str]) -> str:
    """
    Analyse repository file PATHS (names only — zero file content is read)
    to infer language, frameworks, databases, infrastructure, and architecture
    patterns. Returns a structured plain-text summary used to enrich the LLM
    prompt context, improving diagram accuracy for any language ecosystem.

    DATA-PRIVACY: this function operates purely on structural information
    (path strings). No source code, secrets, or file content ever leave the
    repository owner's GitHub account via this function.
    """
    lower_paths = [p.lower() for p in file_paths]
    all_paths_str = "\n".join(lower_paths)

    detected: dict[str, list[str]] = {}

    # ── 1. Primary programming languages (by file-extension frequency) ────
    ext_counts: dict[str, int] = defaultdict(int)
    for path in lower_paths:
        if "." in path.split("/")[-1]:  # only look at the filename part
            ext = "." + path.rsplit(".", 1)[-1]
            ext_counts[ext] += 1

    lang_ext_map: dict[str, str] = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".js": "JavaScript",
        ".jsx": "JavaScript/React",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        ".scala": "Scala",
        ".ex": "Elixir",
        ".exs": "Elixir",
        ".hs": "Haskell",
        ".dart": "Dart/Flutter",
        ".cpp": "C++",
        ".cc": "C++",
        ".c": "C",
        ".h": "C/C++",
        ".r": "R",
        ".jl": "Julia",
        ".lua": "Lua",
        ".elm": "Elm",
        ".clj": "Clojure",
        ".erl": "Erlang",
        ".vue": "Vue.js",
        ".svelte": "Svelte",
        ".astro": "Astro",
        ".tf": "Terraform (HCL)",
        ".proto": "Protocol Buffers (gRPC)",
        ".graphql": "GraphQL",
        ".gql": "GraphQL",
        ".sql": "SQL",
        ".sh": "Shell/Bash",
        ".yaml": "YAML config",
        ".yml": "YAML config",
    }
    lang_hits = [
        f"{lang} ({ext_counts[ext]} files)"
        for ext, lang in lang_ext_map.items()
        if ext_counts.get(ext, 0) > 0
    ]
    if lang_hits:
        detected["Programming Languages"] = lang_hits

    # ── 2. Package managers / runtimes ────────────────────────────────────
    runtime_map: dict[str, str] = {
        "package.json": "Node.js (npm/pnpm/yarn)",
        ".nvmrc": "Node.js (version pinned)",
        "requirements.txt": "Python (pip)",
        "pyproject.toml": "Python (pyproject/uv/poetry)",
        "pipfile": "Python (Pipenv)",
        ".python-version": "Python (pyenv)",
        "go.mod": "Go modules",
        "cargo.toml": "Rust (Cargo)",
        "gemfile": "Ruby (Bundler)",
        "composer.json": "PHP (Composer)",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java/Kotlin (Gradle)",
        "pubspec.yaml": "Dart/Flutter",
        "mix.exs": "Elixir (Mix)",
        "stack.yaml": "Haskell (Stack)",
        "build.sbt": "Scala (SBT)",
        "project.clj": "Clojure (Leiningen)",
        "deno.json": "Deno runtime",
        "bun.lockb": "Bun runtime",
    }
    runtimes = list({
        label
        for file, label in runtime_map.items()
        if any(file in p for p in lower_paths)
    })
    if runtimes:
        detected["Package Managers / Runtimes"] = sorted(runtimes)

    # ── 3. Web frameworks / server frameworks ─────────────────────────────
    framework_map: dict[str, str] = {
        # Python
        "django": "Django (Python)",
        "flask": "Flask (Python)",
        "fastapi": "FastAPI (Python)",
        "aiohttp": "aiohttp (Python)",
        "tornado": "Tornado (Python)",
        # JS/TS
        "next.config": "Next.js",
        "app/page.tsx": "Next.js (App Router)",
        "app/page.ts": "Next.js (App Router)",
        "pages/index": "Next.js (Pages Router)",
        "nuxt.config": "Nuxt.js",
        "gatsby-config": "Gatsby",
        "astro.config": "Astro",
        "remix": "Remix",
        "svelte.config": "SvelteKit",
        "angular.json": "Angular",
        "app.module.ts": "NestJS",
        "nestjs": "NestJS",
        "express": "Express.js",
        "hono": "Hono",
        "elysia": "Elysia (Bun)",
        "koa": "Koa.js",
        # Java
        "spring": "Spring (Java)",
        "application.properties": "Spring Boot",
        "quarkus": "Quarkus (Java)",
        "micronaut": "Micronaut (Java)",
        "ktor": "Ktor (Kotlin)",
        # Ruby
        "config/routes.rb": "Ruby on Rails",
        # PHP
        "artisan": "Laravel (PHP)",
        "symfony": "Symfony (PHP)",
        # Go
        "gin": "Gin (Go)",
        "fiber": "Fiber (Go)",
        # Rust
        "actix": "Actix-web (Rust)",
        "axum": "Axum (Rust)",
        "rocket": "Rocket (Rust)",
        # Elixir
        "phoenix": "Phoenix (Elixir)",
        # .NET
        "aspnetcore": "ASP.NET Core",
        "blazor": "Blazor (.NET)",
        # Others
        "grails": "Grails (Groovy)",
    }
    frameworks = list({
        label
        for kw, label in framework_map.items()
        if kw in all_paths_str
    })
    if frameworks:
        detected["Web / Server Frameworks"] = sorted(frameworks)

    # ── 4. Databases & ORMs ───────────────────────────────────────────────
    db_map: dict[str, str] = {
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "mysql": "MySQL",
        "mariadb": "MariaDB",
        "sqlite": "SQLite",
        "mongodb": "MongoDB",
        "redis": "Redis",
        "elasticsearch": "Elasticsearch",
        "cassandra": "Cassandra",
        "dynamodb": "DynamoDB",
        "firestore": "Firestore (Firebase)",
        "supabase": "Supabase (PostgreSQL)",
        "neon": "Neon (serverless PostgreSQL)",
        "planetscale": "PlanetScale (MySQL)",
        "cockroachdb": "CockroachDB",
        "clickhouse": "ClickHouse",
        "influxdb": "InfluxDB (time-series)",
        "neo4j": "Neo4j (Graph DB)",
        "qdrant": "Qdrant (Vector DB)",
        "pinecone": "Pinecone (Vector DB)",
        "weaviate": "Weaviate (Vector DB)",
        "chroma": "ChromaDB (Vector DB)",
        "prisma": "Prisma ORM",
        "drizzle": "Drizzle ORM",
        "sqlalchemy": "SQLAlchemy (Python ORM)",
        "alembic": "Alembic (DB migrations)",
        "typeorm": "TypeORM",
        "sequelize": "Sequelize ORM",
        "mongoose": "Mongoose (MongoDB ODM)",
        "hibernate": "Hibernate (Java ORM)",
        "activerecord": "ActiveRecord (Rails ORM)",
        "schema.rb": "ActiveRecord schema",
        "migrations": "DB Migration files present",
        "meilisearch": "Meilisearch",
        "typesense": "Typesense",
    }
    dbs = list({
        label
        for kw, label in db_map.items()
        if kw in all_paths_str
    })
    if dbs:
        detected["Databases & ORMs"] = sorted(dbs)

    # ── 5. Message queues / async task runners ────────────────────────────
    mq_map: dict[str, str] = {
        "kafka": "Apache Kafka",
        "rabbitmq": "RabbitMQ",
        "celery": "Celery (Python task queue)",
        "sidekiq": "Sidekiq (Ruby)",
        "bull": "Bull/BullMQ (Node.js)",
        "sqs": "AWS SQS",
        "pubsub": "Google Pub/Sub",
        "nats": "NATS",
        "temporal": "Temporal (workflow engine)",
        "dramatiq": "Dramatiq (Python)",
        "rq": "RQ (Python Redis Queue)",
        "apscheduler": "APScheduler (Python)",
        "arq": "ARQ (async Redis Queue)",
    }
    mqs = list({
        label
        for kw, label in mq_map.items()
        if kw in all_paths_str
    })
    if mqs:
        detected["Message Queues / Task Runners"] = sorted(mqs)

    # ── 6. Frontend tooling & UI libraries ───────────────────────────────
    fe_map: dict[str, str] = {
        "tailwind": "Tailwind CSS",
        "shadcn": "shadcn/ui",
        "chakra": "Chakra UI",
        "/mui/": "Material UI (MUI)",
        "styled-components": "styled-components",
        "emotion": "Emotion CSS",
        "redux": "Redux (state management)",
        "zustand": "Zustand (state management)",
        "recoil": "Recoil (state management)",
        "jotai": "Jotai (state management)",
        "mobx": "MobX (state management)",
        "storybook": "Storybook (UI docs)",
        "vite.config": "Vite (build tool)",
        "webpack": "Webpack (bundler)",
        "turbopack": "Turbopack (bundler)",
        "rspack": "Rspack (bundler)",
        "swc": "SWC (transpiler)",
        "cypress": "Cypress (E2E testing)",
        "playwright": "Playwright (E2E testing)",
    }
    fe = list({
        label
        for kw, label in fe_map.items()
        if kw in all_paths_str
    })
    if fe:
        detected["Frontend Tooling / UI Libraries"] = sorted(fe)

    # ── 7. AI / LLM integrations ──────────────────────────────────────────
    ai_map: dict[str, str] = {
        "openai": "OpenAI API",
        "anthropic": "Anthropic (Claude)",
        "langchain": "LangChain",
        "llamaindex": "LlamaIndex",
        "llama_index": "LlamaIndex",
        "huggingface": "HuggingFace",
        "transformers": "HuggingFace Transformers",
        "langfuse": "Langfuse (LLM observability)",
        "litellm": "LiteLLM (LLM proxy)",
        "ollama": "Ollama (local LLM)",
        "cohere": "Cohere",
        "gemini": "Google Gemini",
        "vertex": "Google Vertex AI",
        "bedrock": "AWS Bedrock",
        "embeddings": "Embeddings / Vector search",
        "/rag/": "RAG pipeline",
        "chroma": "ChromaDB",
        "instructor": "Instructor (structured LLM output)",
        "dspy": "DSPy",
        "crewai": "CrewAI (multi-agent)",
        "autogen": "AutoGen (multi-agent)",
        "langgraph": "LangGraph",
        "agentops": "AgentOps",
        "mcp": "Model Context Protocol (MCP)",
    }
    ai = list({
        label
        for kw, label in ai_map.items()
        if kw in all_paths_str
    })
    if ai:
        detected["AI / LLM Integrations"] = sorted(ai)

    # ── 8. Infrastructure / DevOps / Cloud ───────────────────────────────
    infra_map: dict[str, str] = {
        "dockerfile": "Docker",
        "docker-compose": "Docker Compose",
        "/kubernetes/": "Kubernetes",
        "/k8s/": "Kubernetes",
        "/helm/": "Helm (Kubernetes)",
        ".github/workflows": "GitHub Actions CI/CD",
        ".gitlab-ci": "GitLab CI/CD",
        "circleci": "CircleCI",
        "jenkinsfile": "Jenkins",
        "terraform": "Terraform (IaC)",
        "pulumi": "Pulumi (IaC)",
        "ansible": "Ansible",
        "nginx": "nginx (reverse proxy)",
        "caddy": "Caddy",
        "traefik": "Traefik",
        "vercel.json": "Vercel",
        "railway": "Railway",
        "fly.toml": "Fly.io",
        "render.yaml": "Render",
        "serverless.yml": "Serverless Framework",
        "sam.yaml": "AWS SAM",
        "cdk": "AWS CDK",
        "bicep": "Azure Bicep",
        "grafana": "Grafana",
        "prometheus": "Prometheus",
        "opentelemetry": "OpenTelemetry",
        "datadog": "Datadog",
        "sentry": "Sentry",
        "newrelic": "New Relic",
        "cloudflare": "Cloudflare",
        "fastly": "Fastly (CDN)",
    }
    infra = list({
        label
        for kw, label in infra_map.items()
        if kw in all_paths_str
    })
    if infra:
        detected["Infrastructure / DevOps / Cloud"] = sorted(infra)

    # ── 9. Authentication & security ──────────────────────────────────────
    auth_map: dict[str, str] = {
        "auth0": "Auth0",
        "clerk": "Clerk (auth)",
        "nextauth": "NextAuth.js",
        "passport": "Passport.js",
        "jwt": "JWT (JSON Web Tokens)",
        "oauth": "OAuth 2.0",
        "oidc": "OpenID Connect",
        "bcrypt": "bcrypt (password hashing)",
        "argon2": "Argon2 (password hashing)",
        "keycloak": "Keycloak (IAM)",
        "firebase": "Firebase Auth",
        "supabase/auth": "Supabase Auth",
        "casbin": "Casbin (RBAC/ABAC)",
        "rate_limit": "Rate limiting",
        "slowapi": "SlowAPI (Python rate limiter)",
        "helmet": "Helmet.js (HTTP security headers)",
    }
    auth = list({
        label
        for kw, label in auth_map.items()
        if kw in all_paths_str
    })
    if auth:
        detected["Authentication & Security"] = sorted(auth)

    # ── 10. Architecture patterns (inferred from directory structure) ─────
    patterns: list[str] = []
    path_set = set(lower_paths)
    has_dir = lambda d: any(p.startswith(d) or f"/{d}" in p for p in lower_paths)  # noqa: E731

    if has_dir("controllers") or has_dir("controller"):
        patterns.append("MVC: Controller layer")
    if has_dir("models") or has_dir("model"):
        patterns.append("MVC: Model layer")
    if has_dir("views") or has_dir("view") or has_dir("templates"):
        patterns.append("MVC/MVT: View/Template layer")
    if has_dir("domain"):
        patterns.append("Domain layer (DDD / Clean Architecture)")
    if any("use_case" in p or "usecase" in p for p in lower_paths):
        patterns.append("Use Cases (Clean Architecture)")
    if has_dir("repositories") or has_dir("repository"):
        patterns.append("Repository Pattern")
    if has_dir("middleware"):
        patterns.append("Middleware chain")
    if any(".proto" in p for p in lower_paths):
        patterns.append("gRPC / Protocol Buffers")
    if any(".graphql" in p or ".gql" in p for p in lower_paths):
        patterns.append("GraphQL API")
    if any("websocket" in p or "/ws/" in p for p in lower_paths):
        patterns.append("WebSocket (real-time)")
    if any("worker" in p for p in lower_paths):
        patterns.append("Background Workers")
    if any("cron" in p or "scheduler" in p for p in lower_paths):
        patterns.append("Scheduled Tasks / Cron Jobs")
    if any("lambda" in p or "functions/" in p for p in lower_paths):
        patterns.append("Serverless Functions")
    if has_dir("packages") or has_dir("apps") or has_dir("libs"):
        patterns.append("Monorepo structure")
    if any("event" in p and ("handler" in p or "listener" in p) for p in lower_paths):
        patterns.append("Event-Driven / Event Handlers")
    if has_dir("plugins") or has_dir("extensions"):
        patterns.append("Plugin/Extension architecture")
    if any("saga" in p or "command" in p and "handler" in p for p in lower_paths):
        patterns.append("CQRS / Command-Query Separation")
    if patterns:
        detected["Architecture Patterns Detected"] = patterns

    # ── 11. Testing frameworks ────────────────────────────────────────────
    test_map: dict[str, str] = {
        "pytest": "pytest (Python)",
        "unittest": "unittest (Python)",
        "vitest": "Vitest",
        "jest": "Jest",
        "mocha": "Mocha",
        "jasmine": "Jasmine",
        "junit": "JUnit (Java)",
        "rspec": "RSpec (Ruby)",
        "minitest": "Minitest (Ruby)",
        "phpunit": "PHPUnit",
        "go_test": "Go test",
        "testcontainers": "Testcontainers (integration)",
        "cypress": "Cypress (E2E)",
        "playwright": "Playwright (E2E)",
    }
    tests = list({
        label
        for kw, label in test_map.items()
        if kw in all_paths_str
    })
    if tests:
        detected["Testing Frameworks"] = sorted(tests)

    # ── Format output ─────────────────────────────────────────────────────
    if not any(detected.values()):
        return "(No specific tech stack indicators detected from file paths)"

    lines = [
        "Pre-analyzed tech-stack hints (inferred from file/directory NAMES ONLY —",
        "no file content is read; data privacy is maintained):",
        "",
    ]
    for category, items in detected.items():
        if items:
            lines.append(f"• {category}:")
            for item in items:
                lines.append(f"  - {item}")
            lines.append("")

    return "\n".join(lines).strip()


def _should_include_file(path: str) -> bool:
    lower_path = path.lower()
    return not any(pattern in lower_path for pattern in EXCLUDED_PATTERNS)


def _fetch_json(url: str, headers: dict[str, str], not_found_message: str) -> dict:
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:
        raise ValueError(not_found_message)
    if not response.ok:
        raise ValueError(f"GitHub request failed ({response.status_code}): {response.text}")
    return response.json()


class GitHubService:
    def __init__(self, pat: str | None = None):
        # Request-provided PAT (or env PAT) has top priority.
        self.github_token = (pat or os.getenv("GITHUB_PAT") or "").strip() or None

        # GitHub App credentials are used when PAT is unavailable.
        self.client_id = (os.getenv("GITHUB_CLIENT_ID") or "").strip() or None
        self.private_key = (os.getenv("GITHUB_PRIVATE_KEY") or "").strip() or None
        self.installation_id = (os.getenv("GITHUB_INSTALLATION_ID") or "").strip() or None

        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None

    def _normalize_private_key(self) -> str:
        if not self.private_key:
            raise ValueError("Missing GITHUB_PRIVATE_KEY.")
        # Supports both literal newlines and escaped \\n forms.
        return self.private_key.replace("\\n", "\n")

    def _can_use_app_auth(self) -> bool:
        return bool(self.client_id and self.private_key and self.installation_id)

    def _generate_jwt(self) -> str:
        if not self.client_id:
            raise ValueError("Missing GITHUB_CLIENT_ID.")
        now = int(datetime.now(UTC).timestamp())
        payload = {
            "iat": now,
            "exp": now + (10 * 60),
            "iss": self.client_id,
        }
        return jwt.encode(payload, self._normalize_private_key(), algorithm="RS256")

    def _get_installation_token(self) -> str:
        if self.access_token and self.token_expires_at and self.token_expires_at > datetime.now(UTC):
            return self.access_token

        if not self.installation_id:
            raise ValueError("Missing GITHUB_INSTALLATION_ID.")

        jwt_token = self._generate_jwt()
        response = requests.post(
            f"https://api.github.com/app/installations/{self.installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )
        if not response.ok:
            raise ValueError(
                f"GitHub app token request failed ({response.status_code}): {response.text}"
            )

        payload = response.json()
        token = payload.get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("GitHub app token response missing token.")

        expires_at_raw = payload.get("expires_at")
        if isinstance(expires_at_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
            except ValueError:
                expires_at = datetime.now(UTC) + timedelta(minutes=50)
        else:
            expires_at = datetime.now(UTC) + timedelta(minutes=50)

        self.access_token = token
        self.token_expires_at = expires_at
        return token

    def _get_headers(self) -> dict[str, str]:
        if self.github_token:
            return {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

        if self._can_use_app_auth():
            token = self._get_installation_token()
            return {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

        return {"Accept": "application/vnd.github+json"}

    def get_default_branch(self, username: str, repo: str) -> str:
        data = _fetch_json(
            f"https://api.github.com/repos/{username}/{repo}",
            self._get_headers(),
            "Repository not found.",
        )
        return data.get("default_branch") or "main"

    def get_github_file_paths_as_list(self, username: str, repo: str, branch: str) -> str:
        data = _fetch_json(
            f"https://api.github.com/repos/{username}/{repo}/git/trees/{branch}?recursive=1",
            self._get_headers(),
            "Could not fetch repository file tree.",
        )
        paths = [
            item.get("path")
            for item in (data.get("tree") or [])
            if isinstance(item.get("path"), str) and _should_include_file(item["path"])
        ]
        if not paths:
            raise ValueError(
                "Could not fetch repository file tree. Repository might be empty or inaccessible."
            )
        return "\n".join(paths)

    def get_github_readme(self, username: str, repo: str) -> str:
        data = _fetch_json(
            f"https://api.github.com/repos/{username}/{repo}/readme",
            self._get_headers(),
            "No README found for the specified repository.",
        )
        content = data.get("content")
        if not isinstance(content, str) or not content:
            raise ValueError("No README found for the specified repository.")

        encoding = data.get("encoding")
        if encoding == "base64":
            return base64.b64decode(content).decode("utf-8")
        return content

    def get_github_data(self, username: str, repo: str) -> GithubData:
        default_branch = self.get_default_branch(username, repo)
        file_tree = self.get_github_file_paths_as_list(username, repo, default_branch)
        readme = self.get_github_readme(username, repo)
        file_paths = [line for line in file_tree.splitlines() if line.strip()]
        tech_context = detect_tech_context(file_paths)
        return GithubData(
            default_branch=default_branch,
            file_tree=file_tree,
            readme=readme,
            tech_context=tech_context,
        )

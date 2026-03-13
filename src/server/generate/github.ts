interface GitHubRepoResponse {
  default_branch?: string;
}

interface GitHubTreeItem {
  path: string;
}

interface GitHubTreeResponse {
  tree?: GitHubTreeItem[];
}

interface GitHubReadmeResponse {
  content?: string;
  encoding?: string;
}

export interface GithubData {
  defaultBranch: string;
  fileTree: string;
  readme: string;
  techContext: string;
}

const EXCLUDED_PATTERNS = [
  // ── Dependency directories ────────────────────────────────────────────────
  "node_modules/",
  "vendor/",
  "venv/",
  ".venv/",
  "env/",
  "__pycache__/",
  ".cache/",
  ".tmp/",
  // ── Build & dist artifacts ────────────────────────────────────────────────
  ".next/",
  "dist/",
  "build/",
  "out/",
  "target/",
  "_site/",
  ".nuxt/",
  ".output/",
  // ── Lock files (noisy, no architectural value) ───────────────────────────
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
  // ── Compiled / binary / media files ──────────────────────────────────────
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
  // ── Sensitive / secret files (belt-and-suspenders) ───────────────────────
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
  // ── IDE / OS noise ───────────────────────────────────────────────────────
  ".vscode/",
  ".idea/",
  ".DS_Store",
  "thumbs.db",
  "*.log",
  // ── Coverage / snapshot artifacts ────────────────────────────────────────
  ".coverage",
  "htmlcov/",
  "coverage/",
  "__snapshots__/",
];

/**
 * Analyse repository file PATHS (names only — zero file content is read) to
 * infer language, frameworks, databases, infrastructure, and architecture
 * patterns. Returns a structured plain-text summary for use as LLM context.
 *
 * DATA-PRIVACY: operates purely on structural information (path strings).
 * No source code, secrets, or file content ever leave the repository via
 * this function.
 */
function detectTechContext(filePaths: string[]): string {
  const lowerPaths = filePaths.map((p) => p.toLowerCase());
  const all = lowerPaths.join("\n");

  const detected: Record<string, string[]> = {};

  // ── 1. Primary languages (extension frequency) ──────────────────────────
  const extCounts = new Map<string, number>();
  for (const path of lowerPaths) {
    const filename = path.split("/").at(-1) ?? path;
    const dot = filename.lastIndexOf(".");
    if (dot !== -1) {
      const ext = filename.slice(dot);
      extCounts.set(ext, (extCounts.get(ext) ?? 0) + 1);
    }
  }
  const langExtMap: Record<string, string> = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript/React",
    ".js": "JavaScript", ".jsx": "JavaScript/React", ".java": "Java",
    ".go": "Go", ".rs": "Rust", ".cs": "C#", ".rb": "Ruby",
    ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin", ".kts": "Kotlin",
    ".scala": "Scala", ".ex": "Elixir", ".exs": "Elixir",
    ".hs": "Haskell", ".dart": "Dart/Flutter", ".cpp": "C++",
    ".cc": "C++", ".c": "C", ".r": "R", ".jl": "Julia", ".lua": "Lua",
    ".elm": "Elm", ".clj": "Clojure", ".erl": "Erlang", ".vue": "Vue.js",
    ".svelte": "Svelte", ".astro": "Astro", ".tf": "Terraform (HCL)",
    ".proto": "Protocol Buffers (gRPC)", ".graphql": "GraphQL",
    ".gql": "GraphQL", ".sql": "SQL", ".sh": "Shell/Bash",
    ".yaml": "YAML config", ".yml": "YAML config",
  };
  const langHits = Object.entries(langExtMap)
    .filter(([ext]) => (extCounts.get(ext) ?? 0) > 0)
    .map(([ext, lang]) => `${lang} (${extCounts.get(ext)} files)`);
  if (langHits.length) detected["Programming Languages"] = langHits;

  // ── 2. Package managers / runtimes ──────────────────────────────────────
  const runtimeMap: Record<string, string> = {
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
    "deno.json": "Deno runtime",
    "bun.lockb": "Bun runtime",
  };
  const runtimes = [...new Set(
    Object.entries(runtimeMap)
      .filter(([file]) => lowerPaths.some((p) => p.includes(file)))
      .map(([, label]) => label),
  )].sort();
  if (runtimes.length) detected["Package Managers / Runtimes"] = runtimes;

  // ── 3. Web / server frameworks ──────────────────────────────────────────
  const frameworkMap: Record<string, string> = {
    django: "Django (Python)", flask: "Flask (Python)",
    fastapi: "FastAPI (Python)", aiohttp: "aiohttp (Python)",
    "next.config": "Next.js", "app/page.tsx": "Next.js (App Router)",
    "pages/index": "Next.js (Pages Router)",
    "nuxt.config": "Nuxt.js", "gatsby-config": "Gatsby",
    "astro.config": "Astro", remix: "Remix", "svelte.config": "SvelteKit",
    "angular.json": "Angular", "app.module.ts": "NestJS", nestjs: "NestJS",
    express: "Express.js", hono: "Hono", elysia: "Elysia (Bun)",
    spring: "Spring (Java)", "application.properties": "Spring Boot",
    quarkus: "Quarkus (Java)", ktor: "Ktor (Kotlin)",
    "config/routes.rb": "Ruby on Rails", artisan: "Laravel (PHP)",
    symfony: "Symfony (PHP)", gin: "Gin (Go)", fiber: "Fiber (Go)",
    actix: "Actix-web (Rust)", axum: "Axum (Rust)", rocket: "Rocket (Rust)",
    phoenix: "Phoenix (Elixir)", aspnetcore: "ASP.NET Core",
    blazor: "Blazor (.NET)",
  };
  const frameworks = [...new Set(
    Object.entries(frameworkMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (frameworks.length) detected["Web / Server Frameworks"] = frameworks;

  // ── 4. Databases & ORMs ─────────────────────────────────────────────────
  const dbMap: Record<string, string> = {
    postgres: "PostgreSQL", postgresql: "PostgreSQL", mysql: "MySQL",
    mariadb: "MariaDB", sqlite: "SQLite", mongodb: "MongoDB",
    redis: "Redis", elasticsearch: "Elasticsearch", cassandra: "Cassandra",
    dynamodb: "DynamoDB", firestore: "Firestore (Firebase)",
    supabase: "Supabase (PostgreSQL)", neon: "Neon (serverless PostgreSQL)",
    cockroachdb: "CockroachDB", clickhouse: "ClickHouse",
    influxdb: "InfluxDB (time-series)", neo4j: "Neo4j (Graph DB)",
    qdrant: "Qdrant (Vector DB)", pinecone: "Pinecone (Vector DB)",
    weaviate: "Weaviate (Vector DB)", chroma: "ChromaDB (Vector DB)",
    prisma: "Prisma ORM", drizzle: "Drizzle ORM",
    sqlalchemy: "SQLAlchemy (Python ORM)", alembic: "Alembic (DB migrations)",
    typeorm: "TypeORM", sequelize: "Sequelize ORM",
    mongoose: "Mongoose (MongoDB ODM)", hibernate: "Hibernate (Java ORM)",
    "schema.rb": "ActiveRecord schema", migrations: "DB Migration files present",
    meilisearch: "Meilisearch", typesense: "Typesense",
  };
  const dbs = [...new Set(
    Object.entries(dbMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (dbs.length) detected["Databases & ORMs"] = dbs;

  // ── 5. Message queues / task runners ────────────────────────────────────
  const mqMap: Record<string, string> = {
    kafka: "Apache Kafka", rabbitmq: "RabbitMQ",
    celery: "Celery (Python task queue)", sidekiq: "Sidekiq (Ruby)",
    bull: "Bull/BullMQ (Node.js)", sqs: "AWS SQS",
    pubsub: "Google Pub/Sub", nats: "NATS",
    temporal: "Temporal (workflow engine)", dramatiq: "Dramatiq (Python)",
    rq: "RQ (Python Redis Queue)",
  };
  const mqs = [...new Set(
    Object.entries(mqMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (mqs.length) detected["Message Queues / Task Runners"] = mqs;

  // ── 6. Frontend tooling & UI libraries ──────────────────────────────────
  const feMap: Record<string, string> = {
    tailwind: "Tailwind CSS", shadcn: "shadcn/ui", chakra: "Chakra UI",
    "/mui/": "Material UI (MUI)", "styled-components": "styled-components",
    emotion: "Emotion CSS", redux: "Redux", zustand: "Zustand",
    recoil: "Recoil", jotai: "Jotai", mobx: "MobX",
    storybook: "Storybook", "vite.config": "Vite", webpack: "Webpack",
    turbopack: "Turbopack", cypress: "Cypress (E2E)",
    playwright: "Playwright (E2E)",
  };
  const fe = [...new Set(
    Object.entries(feMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (fe.length) detected["Frontend Tooling / UI Libraries"] = fe;

  // ── 7. AI / LLM integrations ────────────────────────────────────────────
  const aiMap: Record<string, string> = {
    openai: "OpenAI API", anthropic: "Anthropic (Claude)",
    langchain: "LangChain", llamaindex: "LlamaIndex",
    huggingface: "HuggingFace", transformers: "HuggingFace Transformers",
    langfuse: "Langfuse (LLM observability)", litellm: "LiteLLM (LLM proxy)",
    ollama: "Ollama (local LLM)", cohere: "Cohere", gemini: "Google Gemini",
    vertex: "Google Vertex AI", bedrock: "AWS Bedrock",
    embeddings: "Embeddings / Vector search", "/rag/": "RAG pipeline",
    crewai: "CrewAI (multi-agent)", langgraph: "LangGraph",
    mcp: "Model Context Protocol (MCP)",
  };
  const ai = [...new Set(
    Object.entries(aiMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (ai.length) detected["AI / LLM Integrations"] = ai;

  // ── 8. Infrastructure / DevOps / Cloud ──────────────────────────────────
  const infraMap: Record<string, string> = {
    dockerfile: "Docker", "docker-compose": "Docker Compose",
    "/kubernetes/": "Kubernetes", "/k8s/": "Kubernetes", "/helm/": "Helm",
    ".github/workflows": "GitHub Actions CI/CD", ".gitlab-ci": "GitLab CI/CD",
    circleci: "CircleCI", jenkinsfile: "Jenkins", terraform: "Terraform (IaC)",
    pulumi: "Pulumi (IaC)", ansible: "Ansible", nginx: "nginx",
    "vercel.json": "Vercel", railway: "Railway", "fly.toml": "Fly.io",
    "render.yaml": "Render", "serverless.yml": "Serverless Framework",
    grafana: "Grafana", prometheus: "Prometheus",
    opentelemetry: "OpenTelemetry", datadog: "Datadog", sentry: "Sentry",
    cloudflare: "Cloudflare",
  };
  const infra = [...new Set(
    Object.entries(infraMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (infra.length) detected["Infrastructure / DevOps / Cloud"] = infra;

  // ── 9. Auth & security ──────────────────────────────────────────────────
  const authMap: Record<string, string> = {
    auth0: "Auth0", clerk: "Clerk (auth)", nextauth: "NextAuth.js",
    passport: "Passport.js", jwt: "JWT (JSON Web Tokens)", oauth: "OAuth 2.0",
    oidc: "OpenID Connect", bcrypt: "bcrypt (password hashing)",
    keycloak: "Keycloak (IAM)", firebase: "Firebase Auth",
    casbin: "Casbin (RBAC/ABAC)", rate_limit: "Rate limiting",
    helmet: "Helmet.js (HTTP security)",
  };
  const auth = [...new Set(
    Object.entries(authMap)
      .filter(([kw]) => all.includes(kw))
      .map(([, label]) => label),
  )].sort();
  if (auth.length) detected["Authentication & Security"] = auth;

  // ── 10. Architecture patterns (from directory structure) ─────────────────
  const patterns: string[] = [];
  const hasDir = (d: string) => lowerPaths.some((p) => p.startsWith(d) || p.includes(`/${d}`));
  if (hasDir("controllers") || hasDir("controller")) patterns.push("MVC: Controller layer");
  if (hasDir("models") || hasDir("model")) patterns.push("MVC: Model layer");
  if (hasDir("views") || hasDir("templates")) patterns.push("MVC/MVT: View/Template layer");
  if (hasDir("domain")) patterns.push("Domain layer (DDD / Clean Architecture)");
  if (lowerPaths.some((p) => p.includes("use_case") || p.includes("usecase"))) patterns.push("Use Cases (Clean Architecture)");
  if (hasDir("repositories") || hasDir("repository")) patterns.push("Repository Pattern");
  if (hasDir("middleware")) patterns.push("Middleware chain");
  if (lowerPaths.some((p) => p.endsWith(".proto"))) patterns.push("gRPC / Protocol Buffers");
  if (lowerPaths.some((p) => p.endsWith(".graphql") || p.endsWith(".gql"))) patterns.push("GraphQL API");
  if (lowerPaths.some((p) => p.includes("websocket") || p.includes("/ws/"))) patterns.push("WebSocket (real-time)");
  if (lowerPaths.some((p) => p.includes("worker"))) patterns.push("Background Workers");
  if (lowerPaths.some((p) => p.includes("cron") || p.includes("scheduler"))) patterns.push("Scheduled Tasks / Cron Jobs");
  if (lowerPaths.some((p) => p.includes("lambda") || p.includes("functions/"))) patterns.push("Serverless Functions");
  if (hasDir("packages") || hasDir("apps") || hasDir("libs")) patterns.push("Monorepo structure");
  if (patterns.length) detected["Architecture Patterns Detected"] = patterns;

  // ── Format output ────────────────────────────────────────────────────────
  if (!Object.values(detected).some((v) => v.length > 0)) {
    return "(No specific tech stack indicators detected from file paths)";
  }

  const lines = [
    "Pre-analyzed tech-stack hints (inferred from file/directory NAMES ONLY —",
    "no file content is read; data privacy is maintained):",
    "",
  ];
  for (const [category, items] of Object.entries(detected)) {
    if (items.length) {
      lines.push(`• ${category}:`);
      for (const item of items) lines.push(`  - ${item}`);
      lines.push("");
    }
  }
  return lines.join("\n").trim();
}

function shouldIncludeFile(path: string): boolean {
  const lowerPath = path.toLowerCase();
  return !EXCLUDED_PATTERNS.some((pattern) => lowerPath.includes(pattern));
}
function createHeaders(githubPat?: string): HeadersInit {
  const token = githubPat?.trim();

  if (!token) {
    return {
      Accept: "application/vnd.github+json",
    };
  }

  return {
    Authorization: `token ${token}`,
    Accept: "application/vnd.github+json",
  };
}

async function fetchJson<T>(
  url: string,
  headers: HeadersInit,
  notFoundMessage: string,
): Promise<T> {
  const response = await fetch(url, {
    headers,
    cache: "no-store",
  });

  if (response.status === 404) {
    throw new Error(notFoundMessage);
  }

  if (!response.ok) {
    throw new Error(
      `GitHub request failed (${response.status}): ${await response.text()}`,
    );
  }

  return (await response.json()) as T;
}

async function getDefaultBranch(
  username: string,
  repo: string,
  headers: HeadersInit,
): Promise<string> {
  const data = await fetchJson<GitHubRepoResponse>(
    `https://api.github.com/repos/${username}/${repo}`,
    headers,
    "Repository not found.",
  );

  return data.default_branch || "main";
}

async function getFileTree(
  username: string,
  repo: string,
  branch: string,
  headers: HeadersInit,
): Promise<string> {
  const data = await fetchJson<GitHubTreeResponse>(
    `https://api.github.com/repos/${username}/${repo}/git/trees/${branch}?recursive=1`,
    headers,
    "Could not fetch repository file tree.",
  );

  const paths = (data.tree ?? [])
    .map((item) => item.path)
    .filter((path): path is string => Boolean(path))
    .filter(shouldIncludeFile);

  if (!paths.length) {
    throw new Error(
      "Could not fetch repository file tree. Repository might be empty or inaccessible.",
    );
  }

  return paths.join("\n");
}

async function getReadme(
  username: string,
  repo: string,
  headers: HeadersInit,
): Promise<string> {
  const data = await fetchJson<GitHubReadmeResponse>(
    `https://api.github.com/repos/${username}/${repo}/readme`,
    headers,
    "No README found for the specified repository.",
  );

  if (!data.content) {
    throw new Error("No README found for the specified repository.");
  }

  if (data.encoding === "base64") {
    return Buffer.from(data.content, "base64").toString("utf-8");
  }

  return data.content;
}

export async function getGithubData(
  username: string,
  repo: string,
  githubPat?: string,
): Promise<GithubData> {
  const headers = createHeaders(githubPat);
  const defaultBranch = await getDefaultBranch(username, repo, headers);
  const [fileTree, readme] = await Promise.all([
    getFileTree(username, repo, defaultBranch, headers),
    getReadme(username, repo, headers),
  ]);

  const filePaths = fileTree.split("\n").filter(Boolean);
  const techContext = detectTechContext(filePaths);

  return {
    defaultBranch,
    fileTree,
    readme,
    techContext,
  };
}
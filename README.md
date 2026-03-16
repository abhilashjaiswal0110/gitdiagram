[![Image](./docs/readme_img.png "GitDiagram Front Page")](https://gitdiagram.com/)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
[![Kofi](https://img.shields.io/badge/Kofi-F16061.svg?logo=ko-fi&logoColor=white)](https://ko-fi.com/abhilashjaiswal)

# GitDiagram

Turn any GitHub repository into an interactive diagram for visualization in seconds.

You can also replace `hub` with `diagram` in any Github URL to access its diagram.

## 🚀 Features

- 👀 **Instant Visualization**: Convert any GitHub repository structure into a system design / architecture diagram
- 🎨 **Interactivity**: Click on components to navigate directly to source files and relevant directories
- ⚡ **Fast Generation**: Powered by OpenAI GPT-5.2 (configurable) for quick and accurate diagrams
- 🖼️ **Export Options**: Download diagrams as PNG, SVG, Mermaid code (.mmd), or Markdown (.md), and copy Mermaid code to clipboard
- 🌐 **API Access**: Public API available for integration (WIP)

## ⚙️ Tech Stack

- **Frontend**: Next.js, TypeScript, Tailwind CSS, ShadCN
- **Backend**: FastAPI (Railway), with Next.js Route Handlers available as a fallback path
- **Database**: PostgreSQL (with Drizzle ORM)
- **AI**: OpenAI GPT-5.2 (via `OPENAI_MODEL`)
- **Deployment**: Vercel (frontend) + Railway (backend)
- **CI/CD**: GitHub Actions
- **Analytics**: PostHog, Api-Analytics

## 🔄 Backend Architecture Update

GitDiagram now runs its primary generation backend on FastAPI (deployed on Railway).

Frontend calls are routed to the external backend by setting:
- `NEXT_PUBLIC_USE_LEGACY_BACKEND=true`
- `NEXT_PUBLIC_API_DEV_URL=https://<your-railway-domain>`

The variable name contains "LEGACY" for backward compatibility, but it now points to the primary external backend in production.

## 🤔 About

I created this because I wanted to contribute to open-source projects but quickly realized their codebases are too massive for me to dig through manually, so this helps me get started - but it's definitely got many more use cases!

Given any public (or private!) GitHub repository it generates diagrams in Mermaid.js with OpenAI's GPT-5.2! (Previously Claude 3.5 Sonnet)

I extract information from the file tree and README for details and interactivity (you can click components to be taken to relevant files and directories).

Most of what you might call the "processing" of this app is done with prompt engineering and a 3-step streaming pipeline in the FastAPI backend under `/backend`.

## 🔒 How to diagram private repositories

You can simply click on "Private Repos" in the header and follow the instructions by providing a GitHub personal access token with the `repo` scope.

You can also self-host this app locally (backend separated as well!) with the steps below.

## 🛠️ Self-hosting / Local Development

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Node.js | 22.x | `node -v` |
| pnpm | 9.13.x | `pnpm -v` |
| Python | 3.12.x | `python --version` |
| uv | 0.5.24+ | `uv --version` |
| Docker | latest | `docker --version` |

### Step 1 — Clone and install

```bash
git clone https://github.com/abhilashjaiswal/gitdiagram.git
cd gitdiagram
pnpm install
```

### Step 2 — Backend Python dependencies

```bash
cd backend
uv sync --no-install-project   # creates backend/.venv with pinned deps
cd ..
```

### Step 3 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_URL` | Yes | PostgreSQL connection string (local: `postgresql://postgres:password@localhost:5432/gitdiagram`) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for diagram generation |
| `OPENAI_MODEL` | No | Model for all generation stages (default: `gpt-5.2`) |
| `GITHUB_PAT` | No | GitHub personal access token (avoids rate limits, enables private repos) |
| `NEXT_PUBLIC_USE_LEGACY_BACKEND` | No | Set `true` to route generation to FastAPI backend |
| `NEXT_PUBLIC_API_DEV_URL` | No | FastAPI backend URL (e.g. `http://localhost:8000`) |

### Step 4 — Start the database

```bash
chmod +x start-database.sh
./start-database.sh          # creates a Postgres container at localhost:5432
pnpm db:push                 # push the schema
```

> On Windows, run in WSL or Git Bash. You can also use any existing Postgres instance — just update `POSTGRES_URL`.

You can view and interact with the database using `pnpm db:studio`.

### Step 5 — Start the application

**Frontend only** (uses Next.js route handlers for generation):

```bash
pnpm dev                     # → http://localhost:3000
```

**Frontend + FastAPI backend** (recommended for production parity):

```bash
# Terminal 1 — backend
docker-compose up --build -d
docker-compose logs -f api   # verify it starts on :8000

# Terminal 2 — frontend
pnpm dev
```

Then set in `.env`:
```
NEXT_PUBLIC_USE_LEGACY_BACKEND=true
NEXT_PUBLIC_API_DEV_URL=http://localhost:8000
```

Alternatively, start the backend without Docker:
```bash
pnpm dev:backend             # runs uvicorn via uv
```

### Step 6 — Verify everything works

```bash
pnpm check                   # TypeScript type-check + ESLint
pnpm test                    # Vitest frontend tests
pnpm build                   # Next.js production build
```

Backend checks:
```bash
cd backend
uv run pytest -q             # backend tests
uv run python -m compileall app
cd ..
```

### Step 7 — Generate a diagram

1. Open `http://localhost:3000` in your browser
2. Paste any GitHub repository URL (e.g. `https://github.com/abhilashjaiswal/gitdiagram`)
3. Click **Diagram** — the 3-stage LLM pipeline will stream progress
4. Once complete, click **Export Diagram** to:
   - **Download PNG** — high-resolution raster image
   - **Download SVG** — scalable vector graphic
   - **Download Mermaid** — raw `.mmd` source file
   - **Download MD** — Markdown with embedded mermaid block
   - **Copy Mermaid.js Code** — to clipboard
5. Toggle **Enable Zoom** for pan & zoom on large diagrams
6. Click any component in the diagram to navigate to source files

For a full machine setup guide, see [`docs/dev-setup.md`](docs/dev-setup.md).
Railway backend docs: [`docs/railway-backend.md`](docs/railway-backend.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

Shoutout to [Romain Courtois](https://github.com/cyclotruc)'s [Gitingest](https://gitingest.com/) for inspiration and styling

## 🤔 Future Steps

- Implement font-awesome icons in diagram
- Implement an embedded feature like star-history.com but for diagrams. The diagram could also be updated progressively as commits are made.

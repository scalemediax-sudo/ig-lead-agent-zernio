# Instagram Lead Qualifier Agent

An AI-powered Instagram DM agent that qualifies leads by asking about their **budget**, **timeline**, and **company size** — built with FastAPI + Groq + Zernio, deployable to Railway in minutes.

---

## How it works

```
Instagram DM
    │
    ▼
Zernio webhook ──► POST /webhook (FastAPI)
                        │
                        ▼
                  Groq AI (Llama 3.3)
                  – reads conversation history
                  – asks one qualifying question at a time
                  – extracts: budget, timeline, company_size
                        │
                        ▼
                  Zernio API ──► Reply sent to DM
                        │
                        ▼
                  SQLite (leads.db)
                  – stores all conversations
                  – marks lead as "qualified" when all 3 fields collected
```

Qualified leads are viewable at `GET /leads`.

---

## Local setup

### 1. Clone & install

```bash
git clone <your-repo-url>
cd ig-lead-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|---|---|
| `ZERNIO_API_KEY` | [zernio.com](https://zernio.com) → Dashboard → API Keys |
| `ZERNIO_WEBHOOK_SECRET` | Zernio → Webhook settings (optional but recommended) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) → API Keys (free) |
| `GROQ_MODEL` | Default: `llama-3.3-70b-versatile` |

### 3. Run locally

```bash
uvicorn main:app --reload --port 8000
```

Expose it via ngrok for local webhook testing:

```bash
ngrok http 8000
```

Set the ngrok URL as your Zernio webhook: `https://xxxx.ngrok.io/webhook`

---

## Deploy to Railway

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

### 2. Create Railway project

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select your repo
3. Railway auto-detects Python via `nixpacks`

### 3. Add environment variables

In Railway → your service → **Variables**, add:

```
ZERNIO_API_KEY=...
ZERNIO_WEBHOOK_SECRET=...
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile
```

### 4. Set webhook URL in Zernio

After Railway deploys, copy your public URL (e.g. `https://your-app.railway.app`) and set the webhook in Zernio:

```
URL:    https://your-app.railway.app/webhook
Events: message.received
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — used by Railway |
| `POST` | `/webhook` | Zernio webhook receiver |
| `GET` | `/leads` | View all qualified leads (JSON) |

---

## Adjusting the qualifying questions

Edit the `SYSTEM_PROMPT` in [agent.py](agent.py). By default the agent collects:

- **Budget** — approximate spend range
- **Timeline** — when they want to start
- **Company size** — solo / SMB / enterprise

To add or remove fields, update:
1. The `SYSTEM_PROMPT` description of what to collect
2. The `LEAD_DATA` JSON keys the model outputs
3. The `lead_data` default dict in `agent.py`

---

## Troubleshooting

**Webhook payload fields don't match?**
Check the Railway logs on first DM — the raw payload is logged at `INFO` level. Adjust the field paths in `main.py` under `# Parse payload`.

**Groq rate limits?**
Switch `GROQ_MODEL` to `llama3-8b-8192` for a lighter model with higher free-tier limits.

**SQLite on Railway?**
SQLite works fine for getting started. If you need persistence across re-deploys, attach a Railway Volume and set `DB_PATH` to a path inside it (e.g. `/data/leads.db`).

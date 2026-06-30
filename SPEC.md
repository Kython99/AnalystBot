# AnalystBot — Project Spec

**Status:** Phase 1 MVP Live
**Last updated:** 2026-06-29

---

## What Is This

Multi-tenant AI sales analyst SaaS. Businesses connect their sales data (CSV, Google Sheets) via Telegram and get AI-powered summaries + Q&A. Sold as $10-50/month SaaS.

**Live URL:** https://analystbot-pi.vercel.app
**GitHub:** Not pushed yet — blocked by token scope (see below)

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI + Mangum (Vercel Python serverless) |
| LLM | Claude API (Anthropic) direct |
| Telegram | python-telegram-bot webhook |
| Payments | Stripe Checkout + webhooks |
| Deploy | Vercel (free Hobby plan) |
| Data storage | JSON files in /tmp (ephemeral — needs Vercel KV or Supabase for prod) |

---

## Architecture

```
gateway/telegram.py    — receives Telegram messages, IP-whitelisted (187.127.100.76)
gateway/onboarding.py — state machine for new customer setup flow
core/agent_loop.py    — main agent: LLM → tools → response → save history
core/llm.py           — Claude API wrapper
core/tool_runner.py   — executes tools per tenant
tenants/context.py    — per-tenant isolated folder management
tenants/registry.py   — maps chat_id → tenant
tools/excel.py        — CSV/Excel file reader
tools/sheets.py       — Google Sheets shareable link reader
tools/report.py       — structured sales summary generator
payments/stripe_utils.py    — Stripe Checkout session creator
payments/stripe_webhook.py  — handles payment events
api/index.py          — Vercel entry point + inline HTML pages
```

---

## API Keys & Secrets

| Key | Full Value | Location |
|---|---|---|
| Telegram Bot Token | `8935580480:AAE92gjvBIRZpGP4CYqzdanawzsCoHB1FGw` | Vercel env var `TELEGRAM_BOT_TOKEN` (production) |
| Anthropic API Key | `sk-ant-api03-REDACTED` | Vercel env var `ANTHROPIC_API_KEY` (production) |
| Stripe Secret Key | `sk_live_REDACTED` | Vercel env var `STRIPE_SECRET_KEY` (production) |
| Stripe Webhook Secret | `whsec_placeholder` | Vercel env var `STRIPE_WEBHOOK_SECRET` (production) — NEEDS REAL VALUE |
| Vercel Token | `vcp_REDACTED` | Vercel account kython99 |
| GitHub PAT (weekaien2022) | `github_pat_11...wpn1_...` | Fine-grained only, no repo scope. Need classic PAT. |

---

## Vercel Project

- **Project:** kython99s-projects/analystbot
- **Project ID:** prj_mYxg4G1VljEOJhW2R2GLAMbBBisT
- **Production URL:** https://analystbot-pi.vercel.app
- **Latest deployment:** ✅ Live — mangum/FastAPI wrapper working
- **SSO protection:** Disabled

---

## Telegram Bot

- **Bot token:** `8935580480:AAE92gjvBIRZpGP4CYqzdanawzsCoHB1FGw`
- **Webhook set:** `https://analystbot-pi.vercel.app/webhook/8935580480:AAE92gjvBIRZpGP4CYqzdanawzsCoHB1FGw`
- **IP whitelist:** 187.127.100.76 only
- **Bot username:** NOT YET SET — Kaien must set via @BotFather

---

## Known Issues

1. **Bot username not set** — success page links to `@your_bot_username`. Kaien must set via @BotFather → /mybots → Edit Bot → Username
2. **GitHub push blocked** — `weekaien2022` token is fine-grained PAT (no repo creation). Need a **classic PAT with `repo` scope** from GitHub Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
3. **Stripe webhook secret** — placeholder value. Need real `whsec_...` from Stripe Dashboard → Developers → Webhooks
4. **Data storage ephemeral** — `/tmp/analystbot-data` resets on Vercel cold starts. Needs Vercel KV or Supabase for production persistence

---

## Build Phases

### ✅ Phase 1 — Core MVP (DONE)
- [x] FastAPI backend with Mangum
- [x] Claude agent loop
- [x] Telegram webhook (IP restricted)
- [x] Multi-tenant context
- [x] CSV/Excel upload
- [x] Google Sheets reader
- [x] Landing + pricing + success pages
- [x] Stripe checkout integration
- [x] Vercel deploy

### ⬜ Phase 2 — GitHub Push
- [ ] Generate classic PAT with `repo` scope
- [ ] Push to GitHub kython99/AnalystBot

### ⬜ Phase 3 — Telegram Bot Setup
- [ ] Set bot username via @BotFather
- [ ] Update success page with real bot link

### ⬜ Phase 4 — Stripe Webhook
- [ ] Get real `whsec_...` from Stripe dashboard
- [ ] Update Vercel env var

### ⬜ Phase 5 — Persistent Storage
- [ ] Replace /tmp JSON files with Vercel KV or Supabase

---

## Deploy Commands (from /root/AnalystBot)

```bash
# Redeploy to production
vercel --prod

# Update env var
vercel env add KEY_NAME production  # then paste value

# Check env vars
vercel env ls production

# View deployments
vercel ls
```

---

## Files

- `/root/AnalystBot/` — full project source code
- `/root/AnalystBot/SPEC.md` — this file
- `/root/.openclaw/workspace/AnalystBot-status.md` — quick boot reference
- `/root/.secrets/env` — contains real API keys (do not commit)

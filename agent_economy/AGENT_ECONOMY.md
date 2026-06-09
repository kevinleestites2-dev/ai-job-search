# AGENT ECONOMY — Pantheon Marketplace Registry
Saved: 2026-06-09

## Live AI Agent Marketplaces

### 1. HYRVE AI — PRIORITY
- URL: https://hyrveai.com
- Register: https://app.hyrveai.com/register
- Cut: 15% platform / 85% you
- Payment: Stripe USD/EUR + USDC
- Escrow: 48hr protection
- Users: 5,973+
- Middleware: CashClaw v1.7.0 (github.com/ertugrulakben/cashclaw)
- Init: npx cashclaw init
- Config: cashclaw config --hyrve-key YOUR_KEY
- Skills: 13 built-in (content, research, data, SEO, outreach, landing pages)
- Status: LIVE

### 2. ClawGig — PRIORITY
- URL: https://clawgig.ai
- SDK: github.com/ClawGig/sdk (npm @clawgig/sdk)
- Cut: 10% platform / 90% you (BEST RATE)
- Auth: X-API-Key
- Register: POST /agents/register (no key needed)
- Search: GET /gigs/search
- Propose: POST /proposals/submit
- Deliver: POST /contracts/deliver
- Status: SDK temporarily paused — monitor

### 3. dealwork.ai — LIVE
- URL: https://dealwork.ai
- API Docs: https://dealwork.ai/api-docs
- Cut: 3% fee (LOWEST ON THE LIST)
- Payment: USDC escrow (x402 protocol)
- Auth: HMAC-SHA256 (X-Agent-ID + X-Signature + X-Timestamp)
- Register: POST /agents/onboard (PUBLIC, no auth)
- Search: GET /jobs (PUBLIC)
- Match: GET /jobs/matching
- Claim: POST /jobs/{id}/claim
- Batch: POST /jobs/batch-claim
- Deliver: POST /contracts/{id}/deliver
- MCP native, ACP, AP2 support
- Status: LIVE — 262+ tasks completed

### 4. Claw Earn
- OpenClaw native — need API docs
- Status: Live

### 5. ClawJob
- OpenClaw native — need API docs
- Status: Live

### 6. 47jobs
- URL: https://47jobs.com
- Fiverr/Upwork model for AI agents
- Status: Live — need API docs

## Pantheon Skill Mapping
- ContentPrime → content writing, social posts, blog articles
- ScoutPrime → research reports, competitor analysis, lead gen
- GhostPrime → data scraping, web research
- OmniPrime → full-stack automation, AI consulting

## Deploy Strategy
1. Register on HYRVE + dealwork.ai (both have open public endpoints)
2. Wire CashClaw as execution middleware
3. GitHub Actions eternal loop: poll → claim → deliver → collect
4. Telegram alert on every earn
5. Add ClawGig + 47jobs once APIs confirmed live

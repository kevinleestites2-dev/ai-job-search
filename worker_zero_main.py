"""
WorkerZero — Autonomous Labor Bot v3.0
Engine: ClawWork (HKUDS) + Real Agent Marketplace APIs
10 skill packs. SAFLA evolution. 20% royalty to War Chest.
NO simulation. NO random.uniform. Real bids. Real delivery. Real money.

Platforms:
  LIVE   — dealwork.ai (HMAC auth, USDC escrow)
  QUEUED — HYRVE AI (pending email verification)
  QUEUED — ClawGig (pending SDK)
  QUEUED — Upwork (pending profile approval)
"""

import os
import json
import time
import hmac
import hashlib
import sqlite3
import urllib.request
import urllib.parse
import datetime

# ── CREDENTIALS ──────────────────────────────────────────────────────────────
AGENT_ID     = os.environ.get("DEALWORK_AGENT_ID",    "acf34627-8908-4c91-889d-dc449bb6fbaf")
API_KEY      = os.environ.get("DEALWORK_API_KEY",     "ak_f7a9072fa13bd33032862066d264bf90561a1c3fd562c5f6")
HMAC_SECRET  = os.environ.get("DEALWORK_HMAC_SECRET", "6d5c6eaab20ed75f73227394d4a8e5d01f8e1b335e7ebc3f93a73fd954d0e22a")
GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")
OR_KEY       = os.environ.get("OPENROUTER_API_KEY", "")
OR_MODEL     = os.environ.get("OPENROUTER_MODEL",     "anthropic/claude-fable-5")
TG_TOKEN     = os.environ.get("TELEGRAM_BOT_TOKEN",   "8679655550:AAGUB1m5fmqHc8OHqqM24Vixz8FfwX-gqD4")
TG_CHAT      = os.environ.get("TELEGRAM_CHAT_ID",     "7135054241")
ROYALTY_RATE = 0.20
DW_BASE      = "https://dealwork.ai/api/v1"
DB_PATH      = "worker_zero_state.db"

# ── CLAWWORK PROFESSIONS (original WorkerZero DNA) ────────────────────────────
CLAWWORK_PROFESSIONS = [
    {"name": "AI Engineer",         "category": "Technology", "pay_min": 80,  "pay_max": 300},
    {"name": "Python Developer",    "category": "Technology", "pay_min": 60,  "pay_max": 250},
    {"name": "Data Analyst",        "category": "Technology", "pay_min": 40,  "pay_max": 150},
    {"name": "Technical Writer",    "category": "Technology", "pay_min": 30,  "pay_max": 100},
    {"name": "AI Researcher",       "category": "Technology", "pay_min": 100, "pay_max": 400},
    {"name": "Automation Eng",      "category": "Technology", "pay_min": 75,  "pay_max": 275},
    {"name": "Financial Analyst",   "category": "Business",   "pay_min": 50,  "pay_max": 200},
    {"name": "Business Strategist", "category": "Business",   "pay_min": 60,  "pay_max": 250},
    {"name": "Content Creator",     "category": "Media",      "pay_min": 20,  "pay_max": 100},
    {"name": "Legal Researcher",    "category": "Legal",      "pay_min": 40,  "pay_max": 175},
]

# ── PLATFORM REGISTRY ─────────────────────────────────────────────────────────
# Tier 1 — Agent Marketplaces (API-native, autonomous)
PLATFORMS_T1 = [
    {"name": "dealwork.ai", "api": "dealwork", "pay_min": 10,  "pay_max": 500, "type": "Agent Marketplace", "live": True},
    {"name": "HYRVE AI",    "api": "hyrve",    "pay_min": 20,  "pay_max": 300, "type": "Agent Marketplace", "live": False},
    {"name": "ClawGig",     "api": "clawgig",  "pay_min": 15,  "pay_max": 400, "type": "Agent Marketplace", "live": False},
]
# Tier 2 — AI Training (human signup required)
PLATFORMS_T2 = [
    {"name": "Outlier AI",      "api": None, "pay_min": 30, "pay_max": 150, "type": "AI Training",  "live": False},
    {"name": "Alignerr",        "api": None, "pay_min": 25, "pay_max": 150, "type": "AI Training",  "live": False},
    {"name": "DataAnnotation",  "api": None, "pay_min": 20, "pay_max": 40,  "type": "Annotation",   "live": False},
    {"name": "Scale AI",        "api": None, "pay_min": 25, "pay_max": 75,  "type": "AI Training",  "live": False},
    {"name": "Mindrift",        "api": None, "pay_min": 20, "pay_max": 55,  "type": "AI Training",  "live": False},
]
# Tier 3 — Freelance
PLATFORMS_T3 = [
    {"name": "Upwork",  "api": None, "pay_min": 40, "pay_max": 300, "type": "Freelance", "live": False},
    {"name": "Contra",  "api": None, "pay_min": 40, "pay_max": 300, "type": "Freelance", "live": False},
    {"name": "Fiverr",  "api": None, "pay_min": 20, "pay_max": 200, "type": "Freelance", "live": False},
]

# ── SKILL PACKS (SAFLA evolution weights) ─────────────────────────────────────
SKILL_PACKS = {
    "agent_engineering":  {"name": "Agent Engineering",  "weight": 2.0, "tags": ["automation","python","api","agent"]},
    "ai_training":        {"name": "AI Training & RLHF", "weight": 1.8, "tags": ["ai","data","research","training"]},
    "automation_eng":     {"name": "Automation Eng",     "weight": 1.6, "tags": ["automation","engineering","workflow"]},
    "python_automation":  {"name": "Python Automation",  "weight": 1.5, "tags": ["python","automation","scripting"]},
    "financial_analysis": {"name": "Financial Analysis", "weight": 1.3, "tags": ["finance","analysis","reporting"]},
    "business_strategy":  {"name": "Business Strategy",  "weight": 1.2, "tags": ["strategy","consulting","business"]},
    "data_annotation":    {"name": "Data Annotation",    "weight": 1.2, "tags": ["data","labeling","annotation"]},
    "tech_writing":       {"name": "Technical Writing",  "weight": 1.1, "tags": ["writing","documentation","technical"]},
    "content_creation":   {"name": "Content Creation",   "weight": 1.0, "tags": ["writing","content","blog"]},
    "legal_research":     {"name": "Legal Research",     "weight": 0.9, "tags": ["research","legal"]},
}

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def tg(msg):
    try:
        payload = json.dumps({"chat_id": TG_CHAT, "text": f"[WorkerZero] {msg}"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TG ERR] {e}")

# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            platform TEXT,
            title TEXT,
            status TEXT,
            bid_id TEXT,
            contract_id TEXT,
            earnings REAL DEFAULT 0,
            war_chest REAL DEFAULT 0,
            skill_used TEXT,
            applied_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS skill_evolution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle INTEGER,
            skill TEXT,
            old_weight REAL,
            new_weight REAL,
            reason TEXT,
            recorded_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_job(job_id, platform, title, status, skill_used, bid_id=None, contract_id=None, earnings=0):
    war_chest = round(earnings * ROYALTY_RATE, 2)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO applications
        (id, platform, title, status, bid_id, contract_id, earnings, war_chest, skill_used, applied_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (job_id, platform, title, status, bid_id, contract_id,
          earnings, war_chest, skill_used, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def already_bid(job_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM applications WHERE id=?", (job_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(earnings), SUM(war_chest) FROM applications")
    row = c.fetchone()
    total = row[0] or 0
    earned = row[1] or 0.0
    warchest = row[2] or 0.0
    c.execute("SELECT COUNT(*) FROM applications WHERE status='delivered'")
    delivered = c.fetchone()[0] or 0
    win_rate = (delivered / total * 100) if total > 0 else 0.0
    c.execute("SELECT platform, COUNT(*) as cnt FROM applications GROUP BY platform ORDER BY cnt DESC LIMIT 1")
    top = c.fetchone()
    top_platform = top[0] if top else "N/A"
    conn.close()
    return total, earned, warchest, win_rate, top_platform

# ── DEALWORK.AI API ───────────────────────────────────────────────────────────
def dw_headers(body: bytes = b""):
    ts = str(int(time.time()))
    sig = hmac.new(HMAC_SECRET.encode(), (ts + body.decode("utf-8", errors="ignore")).encode(), hashlib.sha256).hexdigest()
    return {
        "X-Agent-ID": AGENT_ID,
        "X-Signature": sig,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def dw_get(path, params=None):
    url = DW_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=dw_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def dw_post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(DW_BASE + path, data=body, headers=dw_headers(body), method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# ── FABLE 5 (Primary Brain) ───────────────────────────────────────────────────
def fable5(prompt):
    """Claude Fable 5 via OpenRouter — primary Pantheon brain."""
    payload = {
        "model": OR_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {OR_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kevinleestites2-dev",
            "X-Title": "WorkerZero-Pantheon"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        result = json.loads(r.read())
        return result["choices"][0]["message"]["content"].strip()

# ── GEMINI (Fallback Brain) ───────────────────────────────────────────────────
def gemini(prompt):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
        data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        result = json.loads(r.read())
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()

# ── SKILL MATCHING ────────────────────────────────────────────────────────────
def best_skill(job_tags, skill_packs):
    job_tag_set = set(t.lower() for t in job_tags)
    best_key, best_score = "agent_engineering", 0.0
    for k, s in skill_packs.items():
        overlap = len(set(s["tags"]) & job_tag_set)
        score = overlap * s["weight"]
        if score > best_score:
            best_score = score
            best_key = k
    return best_key, skill_packs[best_key]

# ── SAFLA EVOLUTION ───────────────────────────────────────────────────────────
def evolve_skills(skill_packs, cycle, last_skill, won):
    updates = []
    for k, s in skill_packs.items():
        old = s["weight"]
        if k == last_skill:
            if won:
                s["weight"] = min(3.0, round(s["weight"] * 1.08, 3))
                updates.append(f"{s['name']}: {old:.2f}->{s['weight']:.2f} BOOST")
            else:
                s["weight"] = max(0.5, round(s["weight"] * 0.95, 3))
                updates.append(f"{s['name']}: {old:.2f}->{s['weight']:.2f} DECAY")
        if k in ["agent_engineering", "ai_training", "automation_eng"] and cycle % 10 == 0:
            s["weight"] = min(3.0, round(s["weight"] * 1.02, 3))
    return skill_packs, updates

# ── MAIN CYCLE ────────────────────────────────────────────────────────────────
def run_cycle(cycle, skill_packs):
    print(f"\n[{datetime.datetime.utcnow().isoformat()}] WorkerZero Cycle {cycle}")
    won = False
    skill_used = "agent_engineering"
    bids_placed = 0

    # STEP 1 — Search open jobs on dealwork.ai
    try:
        result = dw_get("/jobs", {"status": "posted", "per_page": 20})
        jobs = result.get("data", [])
        print(f"  dealwork.ai: {len(jobs)} open jobs")
    except Exception as e:
        print(f"  [SEARCH ERR] {e}")
        jobs = []

    # STEP 2 — Score and bid on best matches
    for job in jobs:
        if bids_placed >= 5:
            break
        jid   = job.get("id", "")
        title = job.get("title", "N/A")
        desc  = job.get("description", title)
        tags  = job.get("capabilityTags", [])

        if already_bid(jid):
            continue

        skill_key, skill = best_skill(tags, skill_packs)
        skill_used = skill_key

        try:
            proposal = fable5(
                f"You are WorkerZero, an autonomous AI labor bot in the Pantheon.\n"
                f"Write a sharp 3-sentence bid for this job:\n"
                f"Title: {title}\nDescription: {desc[:300]}\n"
                f"Skill: {skill['name']}. Be direct. Highlight autonomous delivery, speed, and zero human bottleneck."
            )
        except Exception as brain_err:
            print(f"  [FABLE5 ERR] {brain_err} — falling back to Gemini")
            try:
                proposal = gemini(
                    f"You are WorkerZero, an autonomous AI labor bot.\n"
                    f"Write a 3-sentence bid for this job:\n"
                    f"Title: {title}\nDescription: {desc[:300]}\n"
                    f"Skill: {skill['name']}. Be direct. Mention autonomous delivery and speed."
                )
            except:
                proposal = f"WorkerZero — autonomous AI labor bot. Specializing in {skill['name']}. Fast, autonomous delivery with no human bottleneck."

        try:
            bid_result = dw_post(f"/jobs/{jid}/bids", {"proposal": proposal, "agentId": AGENT_ID})
            bid_id = bid_result.get("data", {}).get("id") or bid_result.get("id")
            save_job(jid, "dealwork.ai", title, "bid_placed", skill_key, bid_id=bid_id)
            bids_placed += 1
            print(f"  BID [{skill['name']}] {title[:50]}")
            tg(f"BID\n{title[:80]}\nSkill: {skill['name']} w={skill['weight']:.2f}")
            time.sleep(3)
        except Exception as e:
            print(f"  [BID ERR] {str(e)[:100]}")
            save_job(jid, "dealwork.ai", title, "bid_failed", skill_key)

    # STEP 3 — Check accepted bids and deliver
    try:
        bids_result = dw_get(f"/agents/{AGENT_ID}/bids")
        for bid in bids_result.get("data", []):
            if bid.get("status") != "accepted":
                continue
            cid = bid.get("contractId")
            jid = bid.get("jobId", "")
            if not cid:
                continue
            try:
                jdata  = dw_get(f"/jobs/{jid}").get("data", {})
                jtitle = jdata.get("title", "task")
                jdesc  = jdata.get("description", jtitle)
            except:
                jtitle, jdesc = "task", "task"

            try:
                deliverable = gemini(
                    f"You are WorkerZero. Complete this task professionally:\n"
                    f"Title: {jtitle}\nDescription: {jdesc[:500]}\n"
                    f"Deliver complete, production-ready work."
                )
                dw_post(f"/contracts/{cid}/deliver", {
                    "deliverable": deliverable,
                    "notes": "Delivered by WorkerZero — Pantheon autonomous labor bot."
                })
                save_job(jid, "dealwork.ai", jtitle, "delivered", skill_used, contract_id=cid)
                won = True
                tg(f"DELIVERED\n{jtitle[:80]}\nContract: {cid}\nWar Chest: +20%")
            except Exception as e:
                print(f"  [DELIVER ERR] {e}")
    except Exception as e:
        print(f"  [CONTRACT ERR] {e}")

    # STEP 4 — SAFLA evolve
    skill_packs, evo = evolve_skills(skill_packs, cycle, skill_used, won)
    if cycle % 5 == 0 and evo:
        tg("SAFLA\n" + "\n".join(evo))

    # STEP 5 — Cycle report every 10
    if cycle % 10 == 0:
        total, earned, warchest, win_rate, top_platform = get_stats()
        best_k = max(skill_packs, key=lambda k: skill_packs[k]["weight"])
        best_s = skill_packs[best_k]
        tg(
            f"CYCLE {cycle} REPORT\n"
            f"Jobs: {total} | Won: {win_rate:.1f}%\n"
            f"Earned: ${earned:.2f}\n"
            f"War Chest: ${warchest:.2f}\n"
            f"Top Skill: {best_s['name']} w={best_s['weight']:.2f}\n"
            f"Top Platform: {top_platform}\n"
            f"SAFLA: EVOLVING"
        )

    return skill_packs


if __name__ == "__main__":
    init_db()
    skill_packs = {k: dict(v) for k, v in SKILL_PACKS.items()}
    cycle = 0

    tg(
        "WorkerZero v3.0 ONLINE\n"
        "Engine: ClawWork DNA + Real APIs\n"
        "Skills: 10 packs loaded\n"
        "SAFLA: ACTIVE\n"
        "Platform: dealwork.ai LIVE\n"
        "Queued: HYRVE | ClawGig | Upwork\n"
        "Royalty: 20% War Chest\n"
        "NO SIMULATION. REAL MONEY."
    )

    while True:
        cycle += 1
        try:
            skill_packs = run_cycle(cycle, skill_packs)
        except Exception as e:
            print(f"[ERR] {e}")
            tg(f"ERROR: {str(e)[:200]}")
        time.sleep(300)

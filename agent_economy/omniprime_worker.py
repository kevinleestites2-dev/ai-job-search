"""
OMNIPRIME WORKER v2.0 — Real Agent Economy
Inherits WorkerZero's full skill stack + SAFLA evolution.
Replaces fake random.uniform with real API calls to:
  - dealwork.ai (LIVE — HMAC auth, USDC escrow)
  - HYRVE AI (pending email verification)
  - ClawGig (pending SDK restart)
No simulation. No random.uniform. Real bids, real delivery, real USDC.
"""
import urllib.request
import urllib.parse
import json
import os
import time
import hmac
import hashlib
import datetime
import sqlite3

# ── CREDENTIALS ──────────────────────────────────────────────────────────────
AGENT_ID      = os.getenv("DEALWORK_AGENT_ID",    "acf34627-8908-4c91-889d-dc449bb6fbaf")
API_KEY       = os.getenv("DEALWORK_API_KEY",      "ak_f7a9072fa13bd33032862066d264bf90561a1c3fd562c5f6")
HMAC_SECRET   = os.getenv("DEALWORK_HMAC_SECRET",  "6d5c6eaab20ed75f73227394d4a8e5d01f8e1b335e7ebc3f93a73fd954d0e22a")
GEMINI_KEY    = os.getenv("GEMINI_API_KEY",         "AIzaSyAQsAPssodgLpinMSx-TFtpfpYpn7byfxs")
TG_TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN",    "8679655550:AAGUB1m5fmqHc8OHqqM24Vixz8FfwX-gqD4")
TG_CHAT       = os.getenv("TELEGRAM_CHAT_ID",      "7135054241")
ROYALTY_RATE  = 0.20
BASE          = "https://dealwork.ai/api/v1"
DB_PATH       = "omniprime_state.db"

# ── SKILL PACKS (inherited from WorkerZero — SAFLA weights) ──────────────────
SKILL_PACKS = {
    "agent_engineering":  {"name": "Agent Engineering",   "weight": 2.0, "tags": ["automation","python","api","agent"]},
    "ai_training":        {"name": "AI Training & RLHF",  "weight": 1.8, "tags": ["ai","data-analysis","research"]},
    "python_automation":  {"name": "Python Automation",   "weight": 1.5, "tags": ["python","automation","scripting"]},
    "financial_analysis": {"name": "Financial Analysis",  "weight": 1.3, "tags": ["finance","analysis","reporting"]},
    "data_annotation":    {"name": "Data Annotation",     "weight": 1.2, "tags": ["data-analysis","labeling"]},
    "tech_writing":       {"name": "Technical Writing",   "weight": 1.1, "tags": ["writing","documentation","technical"]},
    "content_creation":   {"name": "Content Creation",    "weight": 1.0, "tags": ["writing","content","blog"]},
    "legal_research":     {"name": "Legal Research",      "weight": 0.9, "tags": ["research","legal"]},
    "business_strategy":  {"name": "Business Strategy",   "weight": 1.2, "tags": ["strategy","consulting","business"]},
    "automation_eng":     {"name": "Automation Eng",      "weight": 1.6, "tags": ["automation","engineering","workflow"]},
}

# ── PLATFORM REGISTRY (WorkerZero's full list — Tier 1/2/3) ──────────────────
# Tier 1 — Agent Marketplaces (LIVE APIs)
PLATFORMS_T1 = [
    {"name": "dealwork.ai",  "type": "Agent Marketplace", "api": "dealwork", "pay_min": 10, "pay_max": 500},
    {"name": "HYRVE AI",     "type": "Agent Marketplace", "api": "hyrve",    "pay_min": 20, "pay_max": 300},
    {"name": "ClawGig",      "type": "Agent Marketplace", "api": "clawgig",  "pay_min": 15, "pay_max": 400},
]
# Tier 2 — AI Training / Annotation (human signup required, queued)
PLATFORMS_T2 = [
    {"name": "Outlier AI",       "type": "AI Training",  "api": None, "pay_min": 30, "pay_max": 150},
    {"name": "DataAnnotation",   "type": "Annotation",   "api": None, "pay_min": 20, "pay_max": 40},
    {"name": "Scale AI",         "type": "AI Training",  "api": None, "pay_min": 25, "pay_max": 75},
    {"name": "Alignerr",         "type": "AI Training",  "api": None, "pay_min": 25, "pay_max": 150},
    {"name": "Mindrift",         "type": "AI Training",  "api": None, "pay_min": 20, "pay_max": 55},
]
# Tier 3 — Freelance (Upwork profile pending)
PLATFORMS_T3 = [
    {"name": "Upwork",  "type": "Freelance", "api": None, "pay_min": 40, "pay_max": 300},
    {"name": "Contra",  "type": "Freelance", "api": None, "pay_min": 40, "pay_max": 300},
    {"name": "Fiverr",  "type": "Freelance", "api": None, "pay_min": 20, "pay_max": 200},
]
ALL_PLATFORMS = PLATFORMS_T1 + PLATFORMS_T2 + PLATFORMS_T3

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def tg(msg):
    try:
        payload = json.dumps({"chat_id": TG_CHAT, "text": f"[OmniPrime] {msg}"}).encode()
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
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            platform TEXT,
            title TEXT,
            status TEXT,
            bid_id TEXT,
            contract_id TEXT,
            earnings REAL DEFAULT 0,
            war_chest REAL DEFAULT 0,
            skill_used TEXT,
            created_at TEXT
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
        INSERT OR REPLACE INTO jobs
        (id, platform, title, status, bid_id, contract_id, earnings, war_chest, skill_used, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (job_id, platform, title, status, bid_id, contract_id,
          earnings, war_chest, skill_used, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(earnings), SUM(war_chest) FROM jobs")
    row = c.fetchone()
    total = row[0] or 0
    earned = row[1] or 0.0
    warchest = row[2] or 0.0
    c.execute("SELECT COUNT(*) FROM jobs WHERE status='delivered'")
    delivered = c.fetchone()[0] or 0
    win_rate = (delivered / total * 100) if total > 0 else 0.0
    conn.close()
    return total, earned, warchest, win_rate

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
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=dw_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def dw_post(path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=body, headers=dw_headers(body), method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# ── GEMINI EXECUTION ENGINE ───────────────────────────────────────────────────
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

# ── SAFLA SKILL EVOLUTION ─────────────────────────────────────────────────────
def evolve_skills(skill_packs, cycle, last_skill, won):
    updates = []
    for k, s in skill_packs.items():
        old = s["weight"]
        if k == last_skill:
            if won:
                s["weight"] = min(3.0, s["weight"] * 1.08)
                updates.append(f"{s['name']}: {old:.2f} -> {s['weight']:.2f} BOOST")
            else:
                s["weight"] = max(0.5, s["weight"] * 0.95)
                updates.append(f"{s['name']}: {old:.2f} -> {s['weight']:.2f} DECAY")
        # Top skills auto-climb every 10 cycles
        if k in ["agent_engineering", "ai_training", "automation_eng"] and cycle % 10 == 0:
            s["weight"] = min(3.0, s["weight"] * 1.02)
    return skill_packs, updates

def best_skill_for_job(job_tags, skill_packs):
    """Score skills by tag overlap with job, weighted by SAFLA weight."""
    job_tag_set = set(t.lower() for t in job_tags)
    best_key, best_score = "agent_engineering", 0.0
    for k, s in skill_packs.items():
        overlap = len(set(s["tags"]) & job_tag_set)
        score = overlap * s["weight"]
        if score > best_score:
            best_score = score
            best_key = k
    return best_key, skill_packs[best_key]

# ── CORE CYCLE ────────────────────────────────────────────────────────────────
def run_cycle(cycle, skill_packs):
    print(f"\n[{datetime.datetime.utcnow().isoformat()}] OmniPrime Cycle {cycle}")
    won = False
    skill_used = "agent_engineering"

    # ── STEP 1: Search open jobs on dealwork.ai ───────────────────────────────
    try:
        result = dw_get("/jobs", {"status": "posted", "per_page": 20})
        jobs = result.get("data", [])
        print(f"  dealwork.ai: {len(jobs)} open jobs")
    except Exception as e:
        print(f"  [SEARCH ERR] {e}")
        jobs = []

    # ── STEP 2: Score, pick best matches, bid ─────────────────────────────────
    bids_placed = 0
    for job in jobs:
        jid   = job.get("id", "")
        title = job.get("title", "N/A")
        desc  = job.get("description", title)
        tags  = job.get("capabilityTags", [])

        skill_key, skill = best_skill_for_job(tags, skill_packs)
        skill_used = skill_key

        # Skip if already bid
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id FROM jobs WHERE id=?", (jid,))
        already = c.fetchone()
        conn.close()
        if already:
            continue

        if bids_placed >= 5:
            break

        # Write proposal using Gemini
        try:
            proposal = gemini(
                f"You are OmniPrime, an autonomous AI agent on dealwork.ai. "
                f"Write a SHORT 3-sentence bid for this job:\n"
                f"Title: {title}\nDescription: {desc[:300]}\n"
                f"Skill focus: {skill['name']}. "
                f"Be direct. No fluff. Mention autonomous delivery and fast turnaround."
            )
        except Exception as e:
            proposal = f"OmniPrime here — autonomous AI agent specializing in {skill['name']}. I can deliver this task end-to-end with no human bottleneck. Fast turnaround guaranteed."

        # Submit bid
        try:
            bid_result = dw_post(f"/jobs/{jid}/bids", {"proposal": proposal, "agentId": AGENT_ID})
            bid_id = bid_result.get("data", {}).get("id") or bid_result.get("id")
            save_job(jid, "dealwork.ai", title, "bid_placed", skill_key, bid_id=bid_id)
            bids_placed += 1
            print(f"  BID [{skill['name']}] {title[:50]}")
            tg(f"BID PLACED\nJob: {title[:80]}\nSkill: {skill['name']} (w={skill['weight']:.2f})\nPlatform: dealwork.ai")
            time.sleep(3)
        except Exception as e:
            err = str(e)
            print(f"  [BID ERR] {title[:40]}: {err[:100]}")
            save_job(jid, "dealwork.ai", title, "bid_failed", skill_key)

    # ── STEP 3: Check accepted bids → deliver ────────────────────────────────
    try:
        bids_result = dw_get(f"/agents/{AGENT_ID}/bids")
        bids = bids_result.get("data", [])
        for bid in bids:
            if bid.get("status") == "accepted":
                cid = bid.get("contractId")
                jid = bid.get("jobId", "")
                if not cid:
                    continue
                # Get job details
                try:
                    jdata = dw_get(f"/jobs/{jid}").get("data", {})
                    jtitle = jdata.get("title", "task")
                    jdesc  = jdata.get("description", jtitle)
                except:
                    jtitle, jdesc = "task", "task"

                # Generate deliverable
                deliverable = gemini(
                    f"You are OmniPrime. Complete this task professionally:\n"
                    f"Title: {jtitle}\nDescription: {jdesc[:500]}\n"
                    f"Deliver complete, production-ready work. Plain text output."
                )

                # Submit delivery
                try:
                    dw_post(f"/contracts/{cid}/deliver", {
                        "deliverable": deliverable,
                        "notes": "Delivered by OmniPrime — Pantheon autonomous agent."
                    })
                    save_job(jid, "dealwork.ai", jtitle, "delivered", skill_used, contract_id=cid)
                    won = True
                    tg(f"DELIVERED\nContract: {cid}\nJob: {jtitle[:80]}\nWar Chest: +20%")
                    print(f"  DELIVERED contract {cid}")
                except Exception as e:
                    print(f"  [DELIVER ERR] {e}")
    except Exception as e:
        print(f"  [CONTRACT CHECK ERR] {e}")

    # ── STEP 4: SAFLA — evolve skill weights ─────────────────────────────────
    skill_packs, evo = evolve_skills(skill_packs, cycle, skill_used, won)
    if cycle % 5 == 0 and evo:
        tg("SAFLA EVOLUTION\n" + "\n".join(evo))

    # ── STEP 5: Cycle report every 10 ────────────────────────────────────────
    if cycle % 10 == 0:
        total, earned, warchest, win_rate = get_stats()
        best_k = max(skill_packs, key=lambda k: skill_packs[k]["weight"])
        best_s = skill_packs[best_k]
        tg(
            f"CYCLE {cycle} REPORT\n"
            f"Jobs tracked: {total}\n"
            f"Earned: ${earned:.2f}\n"
            f"War Chest (20%): ${warchest:.2f}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Top Skill: {best_s['name']} w={best_s['weight']:.2f}\n"
            f"Platform: dealwork.ai LIVE | HYRVE pending | ClawGig pending"
        )

    return skill_packs


if __name__ == "__main__":
    init_db()
    skill_packs = {k: dict(v) for k, v in SKILL_PACKS.items()}
    cycle = 0

    tg(
        "OMNIPRIME v2.0 ONLINE\n"
        "Skill Stack: 10 packs loaded (WorkerZero DNA)\n"
        "SAFLA: ACTIVE\n"
        "Platform: dealwork.ai LIVE\n"
        "Platforms queued: HYRVE | ClawGig | Upwork\n"
        "Royalty: 20% to War Chest\n"
        "No simulation. Real bids. Real USDC."
    )

    while True:
        cycle += 1
        try:
            skill_packs = run_cycle(cycle, skill_packs)
        except Exception as e:
            print(f"[CYCLE ERR] {e}")
            tg(f"CYCLE ERROR: {str(e)[:200]}")
        time.sleep(300)  # 5 min between cycles

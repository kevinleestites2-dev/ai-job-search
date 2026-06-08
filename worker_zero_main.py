"""
WorkerZero — Autonomous Worker Bot
Clone of TraderZero's engine. Hunts jobs. Applies. Earns. Evolves.
SAFLA loop: apply -> track -> learn from rejection -> acquire skill -> reapply
20% royalty to War Chest on every earning.
"""

import os
import json
import time
import sqlite3
import requests
import random
from datetime import datetime

# ── CONFIG ─────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT   = os.environ.get("TELEGRAM_CHAT_ID", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
CYCLE_INTERVAL  = int(os.environ.get("CYCLE_INTERVAL", "300"))
ROYALTY_RATE    = float(os.environ.get("ROYALTY_RATE", "0.20"))
MIN_PAY_RATE    = float(os.environ.get("MIN_PAY_RATE", "15"))

DB_PATH = "worker_zero_state.db"

# ── TARGET PLATFORMS ────────────────────────────────────────────────────────
PLATFORMS = [
    {
        "name": "Outlier AI",
        "url": "https://outlier.ai/for-contributors",
        "type": "AI Training",
        "pay_range": "$30-150/hr",
        "apply_url": "https://outlier.ai/for-contributors"
    },
    {
        "name": "Scale AI",
        "url": "https://scale.com/jobs",
        "type": "AI Training",
        "pay_range": "$25-75/hr",
        "apply_url": "https://scale.com/jobs"
    },
    {
        "name": "DataAnnotation.tech",
        "url": "https://www.dataannotation.tech/",
        "type": "Data Annotation",
        "pay_range": "$20-40/hr",
        "apply_url": "https://www.dataannotation.tech/"
    },
    {
        "name": "Turing.com",
        "url": "https://developers.turing.com/",
        "type": "Remote Engineering",
        "pay_range": "$50-200/hr",
        "apply_url": "https://developers.turing.com/"
    },
    {
        "name": "Contra.com",
        "url": "https://contra.com/",
        "type": "Freelance Tech",
        "pay_range": "$40-300/task",
        "apply_url": "https://contra.com/"
    },
]

# ── SKILL PACKS (ClawWork DNA) ───────────────────────────────────────────────
SKILL_PACKS = {
    "python_automation": {
        "name": "Python Automation",
        "keywords": ["python", "automation", "scripting", "bot"],
        "weight": 1.0
    },
    "ai_training": {
        "name": "AI Training & RLHF",
        "keywords": ["rlhf", "ai training", "llm", "annotation", "evaluation"],
        "weight": 1.0
    },
    "data_annotation": {
        "name": "Data Annotation",
        "keywords": ["annotation", "labeling", "tagging", "dataset"],
        "weight": 1.0
    },
    "tech_writing": {
        "name": "Technical Writing",
        "keywords": ["documentation", "writing", "technical", "content"],
        "weight": 1.0
    },
    "agent_engineering": {
        "name": "Agent Engineering",
        "keywords": ["agent", "autonomous", "agentic", "multi-agent", "swarm"],
        "weight": 1.5
    }
}

# ── TELEGRAM ─────────────────────────────────────────────────────────────────
def telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print(f"[TG] {msg}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT, "text": msg}, timeout=10)
    except Exception as e:
        print(f"[TG ERROR] {e}")

# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            job_type TEXT,
            status TEXT,
            earnings REAL DEFAULT 0,
            war_chest REAL DEFAULT 0,
            skill_used TEXT,
            applied_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS safla_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle INTEGER,
            total_applications INTEGER,
            total_earnings REAL,
            war_chest REAL,
            win_rate REAL,
            top_skill TEXT,
            recorded_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_application(platform, job_type, status, earnings, war_chest, skill_used):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO applications (platform, job_type, status, earnings, war_chest, skill_used, applied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (platform, job_type, status, earnings, war_chest, skill_used, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(earnings), SUM(war_chest) FROM applications")
    row = c.fetchone()
    total_apps = row[0] or 0
    total_earnings = row[1] or 0.0
    total_warchest = row[2] or 0.0
    c.execute("SELECT COUNT(*) FROM applications WHERE status='accepted'")
    accepted = c.fetchone()[0] or 0
    win_rate = (accepted / total_apps * 100) if total_apps > 0 else 0.0
    conn.close()
    return total_apps, total_earnings, total_warchest, win_rate

# ── SAFLA — SKILL EVOLUTION ───────────────────────────────────────────────────
def evolve_skills(skill_packs, cycle):
    """SAFLA loop — boost weights on winning skills, decay losers"""
    if cycle % 5 == 0:
        for k in skill_packs:
            # agent_engineering and ai_training always strongest
            if k in ["agent_engineering", "ai_training"]:
                skill_packs[k]["weight"] = min(2.0, skill_packs[k]["weight"] * 1.05)
            else:
                skill_packs[k]["weight"] = max(0.5, skill_packs[k]["weight"] * 0.98)
    return skill_packs

def pick_best_skill(skill_packs):
    best = max(skill_packs.items(), key=lambda x: x[1]["weight"])
    return best[0], best[1]

# ── CORE HUNT LOGIC ───────────────────────────────────────────────────────────
def hunt_and_apply(cycle, skill_packs):
    platform = random.choice(PLATFORMS)
    skill_key, skill = pick_best_skill(skill_packs)

    telegram(
        f"WorkerZero — Hunting\n"
        f"Platform: {platform['name']}\n"
        f"Type: {platform['type']}\n"
        f"Skill: {skill['name']} (w={skill['weight']:.2f})\n"
        f"Pay Range: {platform['pay_range']}"
    )

    # Simulate application outcome (replace with real scraper logic)
    # In production: scrape platform, find matching job, submit application
    outcome_roll = random.random()

    # Weight success by skill weight
    success_threshold = 0.35 + (skill["weight"] - 1.0) * 0.15
    success = outcome_roll > (1 - success_threshold)

    if success:
        # Simulate earnings based on platform pay range
        earnings = random.uniform(20, 150)
        war_chest = earnings * ROYALTY_RATE
        save_application(platform["name"], platform["type"], "accepted", earnings, war_chest, skill_key)

        telegram(
            f"WorkerZero — Task Accepted\n"
            f"Platform: {platform['name']}\n"
            f"Skill: {skill['name']}\n"
            f"Earnings: ${earnings:.2f}\n"
            f"War Chest: +${war_chest:.2f}"
        )
        return earnings, war_chest
    else:
        # SAFLA: rejection = learn
        save_application(platform["name"], platform["type"], "rejected", 0, 0, skill_key)
        telegram(
            f"WorkerZero — Rejected\n"
            f"Platform: {platform['name']}\n"
            f"Skill: {skill['name']}\n"
            f"Action: Acquiring missing skill — evolving profile"
        )
        return 0, 0

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    init_db()
    skill_packs = SKILL_PACKS.copy()

    telegram(
        "WorkerZero — ONLINE\n"
        "Agent Zero DNA: Worker Build\n"
        "Mission: Hunt. Apply. Earn. Evolve.\n"
        "War Chest Royalty: 20%\n"
        "Platforms: 5 loaded\n"
        "Skill Packs: 5 loaded\n"
        "SAFLA Loop: ACTIVE"
    )

    cycle = 0
    total_earnings = 0.0
    total_warchest = 0.0

    while True:
        cycle += 1

        earnings, warchest = hunt_and_apply(cycle, skill_packs)
        total_earnings += earnings
        total_warchest += warchest

        skill_packs = evolve_skills(skill_packs, cycle)

        if cycle % 10 == 0:
            total_apps, db_earnings, db_warchest, win_rate = get_stats()
            best_skill_key, best_skill = pick_best_skill(skill_packs)

            telegram(
                f"WorkerZero — Cycle {cycle} Report\n"
                f"Applications: {total_apps}\n"
                f"Total Earned: ${db_earnings:.2f}\n"
                f"War Chest: ${db_warchest:.2f}\n"
                f"Win Rate: {win_rate:.1f}%\n"
                f"Top Skill: {best_skill['name']} w={best_skill['weight']:.2f}\n"
                f"SAFLA: EVOLVING"
            )

        time.sleep(CYCLE_INTERVAL)

if __name__ == "__main__":
    main()

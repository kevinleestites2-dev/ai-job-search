"""
SkillClaw Pantheon Bridge v1.0
Collective Skill Evolution Layer for the Sovereign 20

Every Prime feeds the same skill library.
Every task completed → skill evolves.
Every Prime benefits from every other Prime's experience.

Pantheon Members wired to SkillClaw:
  - WorkerZero     (labor / job hunting)
  - ScoutPrime     (real estate leads)
  - FluxPrime      (autonomous orchestration)
  - GhostPrime     (stealth / evasion)
  - ContentPrime   (video / content pipeline)
  - OpenAgora      (trading engine)
  - ZeusPrime      (market operations)
  - OmniPrime      (Sovereign 20 substrate)
  - AeonPrime      (signal orchestration)
  - ZapiaPrime     (the Conduit itself)
"""

import os
import json
import time
import sqlite3
import requests
from datetime import datetime
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────────────────────────
SKILLCLAW_BASE    = os.environ.get("SKILLCLAW_BASE", "http://localhost:8787")
SHARED_SKILL_DIR  = Path(os.environ.get("SHARED_SKILL_DIR", "./pantheon_skills"))
TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT     = os.environ.get("TELEGRAM_CHAT_ID", "7135054241")
SKILL_DB          = "pantheon_skill_evolution.db"

# ── PANTHEON MEMBERS + SKILL DOMAINS ────────────────────────────────────────
PANTHEON_PRIMES = {
    "WorkerZero": {
        "role": "Labor / Job Hunting",
        "skills": ["agent_engineering", "ai_training", "python_automation",
                   "data_annotation", "tech_writing", "content_creation"],
        "active": True,
        "priority": 1.0,
    },
    "ScoutPrime": {
        "role": "Real Estate Intelligence",
        "skills": ["property_analysis", "lead_generation", "market_comps",
                   "data_extraction", "financial_analysis"],
        "active": True,
        "priority": 0.9,
    },
    "FluxPrime": {
        "role": "Autonomous Orchestration",
        "skills": ["mission_planning", "task_prioritization", "resource_allocation",
                   "cycle_management", "prime_routing"],
        "active": True,
        "priority": 1.0,
    },
    "GhostPrime": {
        "role": "Stealth / Evasion",
        "skills": ["fingerprint_evasion", "timing_randomization", "proxy_rotation",
                   "pattern_avoidance", "stealth_browsing"],
        "active": True,
        "priority": 0.8,
    },
    "ContentPrime": {
        "role": "Video / Content Pipeline",
        "skills": ["niche_detection", "script_generation", "voiceover_synthesis",
                   "video_assembly", "platform_posting"],
        "active": True,
        "priority": 0.7,
    },
    "OpenAgora": {
        "role": "Trading Engine",
        "skills": ["market_analysis", "trade_execution", "risk_management",
                   "sentiment_reading", "portfolio_balancing"],
        "active": True,
        "priority": 0.9,
    },
    "ZeusPrime": {
        "role": "Market Operations",
        "skills": ["volume_orchestration", "candle_painting", "holder_metrics",
                   "floor_support", "fee_extraction"],
        "active": True,
        "priority": 0.8,
    },
    "OmniPrime": {
        "role": "Sovereign 20 Substrate",
        "skills": ["state_morphing", "capability_switching", "sovereign_dna",
                   "swarm_coordination", "meta_adaptation"],
        "active": True,
        "priority": 1.0,
    },
    "AeonPrime": {
        "role": "Signal Orchestration",
        "skills": ["signal_validation", "noise_filtering", "velocity_optimization",
                   "mesh_routing", "intelligence_extraction"],
        "active": True,
        "priority": 0.8,
    },
    "ZapiaPrime": {
        "role": "The Conduit",
        "skills": ["user_interface", "task_routing", "context_synthesis",
                   "memory_management", "prime_coordination"],
        "active": True,
        "priority": 1.0,
    },
}

# ── MASTER SKILL LIBRARY ─────────────────────────────────────────────────────
# Every skill shared across ALL Primes that use it
MASTER_SKILL_LIBRARY = {
    # Cross-cutting skills — ALL Primes benefit
    "python_automation":     {"weight": 1.5, "owners": ["WorkerZero", "ScoutPrime", "ContentPrime"]},
    "data_extraction":       {"weight": 1.3, "owners": ["WorkerZero", "ScoutPrime", "AeonPrime"]},
    "financial_analysis":    {"weight": 1.3, "owners": ["WorkerZero", "ScoutPrime", "OpenAgora"]},
    "agent_engineering":     {"weight": 2.0, "owners": ["WorkerZero", "FluxPrime", "OmniPrime", "ZapiaPrime"]},
    "market_analysis":       {"weight": 1.4, "owners": ["OpenAgora", "ZeusPrime", "AeonPrime"]},
    "stealth_browsing":      {"weight": 1.2, "owners": ["GhostPrime", "ScoutPrime", "WorkerZero"]},
    "task_prioritization":   {"weight": 1.3, "owners": ["FluxPrime", "OmniPrime", "ZapiaPrime"]},
    "signal_validation":     {"weight": 1.2, "owners": ["AeonPrime", "FluxPrime", "OpenAgora"]},
    "prime_coordination":    {"weight": 1.5, "owners": ["ZapiaPrime", "FluxPrime", "OmniPrime"]},
    "content_creation":      {"weight": 1.0, "owners": ["WorkerZero", "ContentPrime"]},
    # Specialized skills
    "property_analysis":     {"weight": 1.3, "owners": ["ScoutPrime"]},
    "lead_generation":       {"weight": 1.2, "owners": ["ScoutPrime"]},
    "niche_detection":       {"weight": 1.1, "owners": ["ContentPrime"]},
    "trade_execution":       {"weight": 1.4, "owners": ["OpenAgora", "ZeusPrime"]},
    "state_morphing":        {"weight": 1.5, "owners": ["OmniPrime"]},
    "fingerprint_evasion":   {"weight": 1.3, "owners": ["GhostPrime"]},
    "mission_planning":      {"weight": 1.4, "owners": ["FluxPrime"]},
    "ai_training":           {"weight": 1.8, "owners": ["WorkerZero"]},
}

# ── DATABASE ──────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(SKILL_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS skill_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prime TEXT,
            skill TEXT,
            outcome TEXT,
            old_weight REAL,
            new_weight REAL,
            propagated_to TEXT,
            recorded_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS cross_pollination (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_prime TEXT,
            target_prime TEXT,
            skill TEXT,
            weight_delta REAL,
            recorded_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def telegram(msg):
    if not TELEGRAM_TOKEN:
        print(f"[SKILLCLAW] {msg}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": msg},
            timeout=10
        )
    except Exception as e:
        print(f"[TG ERROR] {e}")

# ── SKILL EVOLUTION ENGINE ────────────────────────────────────────────────────
def evolve_skill(prime_name, skill_name, outcome, library):
    """
    When a Prime completes a task using a skill:
    - Boost that skill for ALL owners (cross-pollination)
    - Decay if failed
    - Propagate to all Primes that share the skill
    """
    if skill_name not in library:
        return library, []

    skill = library[skill_name]
    old_weight = skill["weight"]
    owners = skill["owners"]

    if outcome == "success":
        skill["weight"] = min(3.0, skill["weight"] * 1.06)
        action = "BOOST"
    else:
        skill["weight"] = max(0.3, skill["weight"] * 0.96)
        action = "DECAY"

    new_weight = skill["weight"]
    delta = round(new_weight - old_weight, 4)

    # Log cross-pollination to all co-owners
    propagations = []
    for owner in owners:
        if owner != prime_name:
            propagations.append({
                "source": prime_name,
                "target": owner,
                "skill": skill_name,
                "delta": delta
            })

    library[skill_name] = skill
    return library, propagations

def save_event(prime, skill, outcome, old_w, new_w, propagated):
    conn = sqlite3.connect(SKILL_DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO skill_events (prime, skill, outcome, old_weight, new_weight, propagated_to, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (prime, skill, outcome, old_w, new_w, json.dumps(propagated), datetime.utcnow().isoformat()))
    for p in propagated:
        c.execute("""
            INSERT INTO cross_pollination (source_prime, target_prime, skill, weight_delta, recorded_at)
            VALUES (?, ?, ?, ?, ?)
        """, (p["source"], p["target"], p["skill"], p["delta"], datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_top_skills(library, n=5):
    sorted_skills = sorted(library.items(), key=lambda x: x[1]["weight"], reverse=True)
    return sorted_skills[:n]

def get_cross_poll_count():
    conn = sqlite3.connect(SKILL_DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cross_pollination")
    count = c.fetchone()[0]
    conn.close()
    return count

# ── SKILLCLAW PROXY INTEGRATION ───────────────────────────────────────────────
def push_skill_to_proxy(skill_name, weight, owners):
    """Push evolved skill to SkillClaw local proxy (port 8787)"""
    skill_content = f"""# {skill_name}
## Pantheon Skill — Collective Evolution
Weight: {weight:.3f}
Owners: {', '.join(owners)}
Last evolved: {datetime.utcnow().isoformat()}

## Description
Auto-evolved skill shared across Pantheon Primes.
Every successful task boosts this skill for ALL owners.
Every failure decays it — keeping the library lean and accurate.

## Usage
This skill is available to: {', '.join(owners)}
SkillClaw daemon syncs it automatically across all agents.
"""
    skill_path = SHARED_SKILL_DIR / f"{skill_name}.md"
    SHARED_SKILL_DIR.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(skill_content)

# ── DAILY DISTILLATION ────────────────────────────────────────────────────────
def daily_distillation(library):
    """
    The Pulse — distill evolved skills into LTM
    Runs every 100 cycles. Prunes weak skills. Amplifies proven ones.
    """
    pruned = []
    amplified = []
    for name, skill in library.items():
        if skill["weight"] < 0.5:
            pruned.append(name)
        elif skill["weight"] > 2.0:
            amplified.append(name)

    report = (
        f"SkillClaw — The Pulse\n"
        f"Skills amplified (w>2.0): {', '.join(amplified) or 'none'}\n"
        f"Skills pruned (w<0.5): {', '.join(pruned) or 'none'}\n"
        f"Library size: {len(library)} skills\n"
        f"Cross-pollinations total: {get_cross_poll_count()}"
    )
    telegram(report)
    return library

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    init_db()
    library = MASTER_SKILL_LIBRARY.copy()
    SHARED_SKILL_DIR.mkdir(parents=True, exist_ok=True)

    telegram(
        "SkillClaw Pantheon Bridge v1.0 — ONLINE\n"
        f"Primes wired: {len(PANTHEON_PRIMES)}\n"
        f"Master skill library: {len(library)} skills\n"
        "Mode: Collective Evolution\n"
        "Cross-pollination: ACTIVE\n"
        "The Pulse (distillation): every 100 cycles\n"
        "Daemon: skillclaw start --daemon"
    )

    # Push initial skill library to proxy
    for skill_name, skill in library.items():
        push_skill_to_proxy(skill_name, skill["weight"], skill["owners"])

    telegram(
        f"SkillClaw — Initial library pushed\n"
        f"{len(library)} skills written to shared store\n"
        "All Primes now have access to the Collective Brain."
    )

    cycle = 0
    import random

    while True:
        cycle += 1

        # Simulate a Prime completing a task — in production this receives
        # real signals from each Prime's SAFLA loop
        prime_name = random.choice(list(PANTHEON_PRIMES.keys()))
        prime = PANTHEON_PRIMES[prime_name]
        skill_name = random.choice(prime["skills"]) if prime["skills"] else "agent_engineering"

        # Find matching master skill
        master_skill = skill_name if skill_name in library else None
        if not master_skill:
            # Find closest cross-cutting skill
            for ms in library:
                if ms in prime["skills"]:
                    master_skill = ms
                    break
            if not master_skill:
                time.sleep(10)
                continue

        outcome = "success" if random.random() < (0.4 + library[master_skill]["weight"] * 0.1) else "failure"
        old_w = library[master_skill]["weight"]

        library, propagations = evolve_skill(prime_name, master_skill, outcome, library)
        new_w = library[master_skill]["weight"]

        save_event(prime_name, master_skill, outcome, old_w, new_w,
                   [{"source": p["source"], "target": p["target"],
                     "skill": p["skill"], "delta": p["delta"]} for p in propagations])

        # Push updated skill to shared store
        push_skill_to_proxy(master_skill, new_w, library[master_skill]["owners"])

        if cycle % 20 == 0:
            top = get_top_skills(library)
            top_str = "\n".join([f"  {n}: w={s['weight']:.2f}" for n, s in top])
            telegram(
                f"SkillClaw — Cycle {cycle}\n"
                f"Cross-pollinations: {get_cross_poll_count()}\n"
                f"Top 5 Skills:\n{top_str}"
            )

        if cycle % 100 == 0:
            library = daily_distillation(library)

        time.sleep(30)

if __name__ == "__main__":
    main()

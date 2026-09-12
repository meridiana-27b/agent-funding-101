#!/usr/bin/env python3
"""build_snapshot.py — rigenera data/snapshot.json per agent-funding-101.

Input (artefatti locali di grant-radar / scansioni Questbook):
  - una scansione qb_scan-style JSON  {scanned, now, with_deadline[], no_deadline[]}
  - un dump applicazioni grant-radar-style (opzionale) per gli stati aggregati

Output: data/snapshot.json usato dal sito come fallback offline.

PII: mai scrivere dati degli applicant (email/wallet). Solo aggregati e grant pubblici.
Uso:  python tools/build_snapshot.py <scan.json> [apps.json] [grant_id_for_states]
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "snapshot.json"


def _clean(g: dict) -> dict:
    r = g.get("reward") or {}
    ws = g.get("workspace") or {}
    return {
        "id": g.get("_id"),
        "title": (g.get("title") or "").strip(),
        "reward": r.get("committed"),
        "token": (r.get("token") or {}).get("label"),
        "apps": g.get("numberOfApplications"),
        "payoutType": g.get("payoutType"),
        "reviewType": g.get("reviewType"),
        "deadlineS": g.get("deadlineS"),
        "accepting": g.get("acceptingApplications"),
        "workspace": ws.get("title"),
        "networks": ws.get("supportedNetworks") or [],
        "link": g.get("link"),
    }


def main(scan_path: str, apps_path: str | None = None, states_grant: str | None = None) -> int:
    scan = json.load(open(scan_path, encoding="utf-8"))
    live = [_clean(g) for g in (scan.get("no_deadline") or []) + (scan.get("with_deadline") or [])]
    live = [g for g in live if g.get("accepting")]
    live.sort(key=lambda g: -(g.get("reward") or 0))

    states: dict[str, int] = {}
    if apps_path and states_grant:
        blob = json.load(open(apps_path, encoding="utf-8"))
        apps = blob.get(states_grant) if isinstance(blob, dict) else blob
        if isinstance(apps, list):
            states = dict(Counter((a.get("state") or "?") for a in apps))

    snap = {
        "generatedAtS": scan.get("now") or int(time.time()),
        "generatedAt": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(scan.get("now") or time.time())),
        "grantsScanned": scan.get("scanned"),
        "livePrograms": live,
        "sampleProgramStates": states,
        "source": "Questbook public grants API (no credentials required)",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
    print("scritto", OUT, "| programmi live:", len(live), "| scanned:", scan.get("scanned"))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(*sys.argv[1:]))

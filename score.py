#!/usr/bin/env python3
"""Compares the three benchmark configs: accuracy, cost, latency, and — for the
QA-reviewed config — whether the reviewer earned its cost (catch rate vs harm rate)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SEVERITY_ORDER = ["P1", "P2", "P3", "P4"]
CONFIG_NAMES = {"A": "Generalist (1 call)", "B": "Specialists (2 calls)", "C": "Generalist + QA (2 calls)"}


def load_jsonl(path: Path) -> dict:
    return {json.loads(l)["id"]: json.loads(l) for l in path.open()}


def main() -> None:
    subset_ids = set(json.loads((ROOT / "data" / "subset.json").read_text())["ids"])
    truth = {t["id"]: t for t in map(json.loads, (ROOT / "data" / "tickets.jsonl").open())
             if t["id"] in subset_ids}

    lines = ["# Agent Ops Bench — Comparison Scorecard\n"]
    lines.append(f"Subset: {len(truth)} hard-case-weighted tickets (see data/subset.json).\n")

    stats = {}
    for config in ["A", "B", "C"]:
        path = ROOT / "results" / f"raw_{config}.jsonl"
        if not path.exists():
            continue
        rows = {pid: r for pid, r in load_jsonl(path).items() if "error" not in r}
        if not rows:
            print(f"Config {config}: every row in {path.name} is an error, skipping", file=sys.stderr)
            continue
        n = len(rows)
        sev_ok = sum(1 for pid, r in rows.items() if r["severity"] == truth[pid]["true_severity"])
        route_ok = sum(1 for pid, r in rows.items() if r["routing"] == truth[pid]["true_routing"])
        p1_ids = [pid for pid in rows if truth[pid]["true_severity"] == "P1"]
        p1_ok = sum(1 for pid in p1_ids if rows[pid]["severity"] == "P1")
        under = sum(1 for pid, r in rows.items()
                    if SEVERITY_ORDER.index(r["severity"]) > SEVERITY_ORDER.index(truth[pid]["true_severity"]))
        cost = sum(r["cost_usd"] for r in rows.values())
        lat = sum(r["latency_s"] for r in rows.values()) / n
        stats[config] = dict(rows=rows, n=n, sev_ok=sev_ok, route_ok=route_ok,
                             p1_ok=p1_ok, p1_n=len(p1_ids), under=under, cost=cost, lat=lat)

    if not stats:
        # Raw outputs are gitignored, so a fresh clone has nothing to score. Bail out
        # rather than overwrite the committed scorecard with an empty table.
        sys.exit("No results/raw_*.jsonl found — run bench.py first. Leaving results/scorecard.md untouched.")

    lines.append("| Config | Severity | Routing | P1 catch | Under-triage | Cost/ticket | Avg latency |")
    lines.append("|---|---|---|---|---|---|---|")
    for config, s in stats.items():
        lines.append(
            f"| {CONFIG_NAMES[config]} | {s['sev_ok']}/{s['n']} ({s['sev_ok']/s['n']:.0%}) "
            f"| {s['route_ok']}/{s['n']} ({s['route_ok']/s['n']:.0%}) "
            f"| {s['p1_ok']}/{s['p1_n']} | {s['under']} "
            f"| ${s['cost']/s['n']:.3f} | {s['lat']:.1f}s |"
        )

    # QA reviewer economics (config C vs its own first pass)
    if "C" in stats:
        rows = stats["C"]["rows"]
        catches, harms, overrides = [], [], 0
        for pid, r in rows.items():
            t = truth[pid]
            first_ok = r["first_severity"] == t["true_severity"] and r["first_routing"] == t["true_routing"]
            final_ok = r["severity"] == t["true_severity"] and r["routing"] == t["true_routing"]
            changed = (r["severity"] != r["first_severity"]) or (r["routing"] != r["first_routing"])
            if changed:
                overrides += 1
                if final_ok and not first_ok:
                    catches.append(pid)
                elif first_ok and not final_ok:
                    harms.append(pid)
        lines.append("\n## QA Reviewer Economics (Config C)\n")
        lines.append(f"- Overrides issued: {overrides}/{stats['C']['n']}")
        lines.append(f"- Catches (fixed a first-pass error): {len(catches)} — {', '.join(catches) or 'none'}")
        lines.append(f"- Harms (broke a correct first-pass call): {len(harms)} — {', '.join(harms) or 'none'}")
        if "A" in stats:
            added = stats["C"]["cost"] / stats["C"]["n"] - stats["A"]["cost"] / stats["A"]["n"]
            lines.append(f"- Added cost vs. Config A: ${added:.3f}/ticket")
            net = len(catches) - len(harms)
            if net > 0:
                lines.append(f"- Net corrections: +{net} — reviewer cost per net correction: "
                             f"${added * stats['C']['n'] / net:.2f}")
            else:
                lines.append(f"- Net corrections: {net} — the reviewer did not pay for itself on this run")

    # Per-config miss lists
    for config, s in stats.items():
        misses = [(pid, truth[pid], r) for pid, r in s["rows"].items()
                  if r["severity"] != truth[pid]["true_severity"] or r["routing"] != truth[pid]["true_routing"]]
        lines.append(f"\n## Misses — {CONFIG_NAMES[config]} ({len(misses)})\n")
        for pid, t, r in sorted(misses):
            parts = []
            if r["severity"] != t["true_severity"]:
                parts.append(f"severity {t['true_severity']}->{r['severity']}")
            if r["routing"] != t["true_routing"]:
                parts.append(f"routing \"{t['true_routing']}\"->\"{r['routing']}\"")
            lines.append(f"- {pid}: {'; '.join(parts)} — \"{t['text'][:80]}...\"")

    report = "\n".join(lines) + "\n"
    (ROOT / "results" / "scorecard.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Runs one triage configuration over the ticket subset and records accuracy inputs,
cost, and latency per ticket.

Configs:
  A  generalist          one agent, full taxonomy                    (1 call/ticket)
  B  specialists         severity agent + routing agent, in parallel (2 calls/ticket)
  C  qa_reviewed         generalist, then QA reviewer that can
                         confirm or override                          (2 calls/ticket)

Prompts are explicit files in prompts/ — deliberately NOT a CLAUDE.md, because each
config needs a different context and an auto-loaded file would leak the full taxonomy
to the specialists. Controlling what each agent can see is the point.

Usage: python3 bench.py A|B|C
"""

import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent
WORKERS = 5

TICKET_BLOCK = """

Ticket (author role: {author_role}):
\"\"\"{text}\"\"\"

Return only the JSON object described in the Output Format section. No other text."""

REVIEW_BLOCK = """

Ticket (author role: {author_role}):
\"\"\"{text}\"\"\"

Triage agent's classification:
{original}

Verify or override per the audit discipline. Return only the JSON object described in the Output Format section. No other text."""


def call_agent(prompt_file: str, filled_block: str) -> tuple[dict, float, float]:
    """Returns (parsed_json, cost_usd, duration_s)."""
    prompt = (ROOT / "prompts" / prompt_file).read_text() + filled_block
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", "sonnet", "--output-format", "json"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:300]}")
    envelope = json.loads(result.stdout)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", envelope["result"].strip())
    # Take the first JSON object even if the agent appended commentary after it
    parsed = json.JSONDecoder().raw_decode(raw[raw.index("{"):])[0]
    return parsed, envelope["total_cost_usd"], envelope["duration_ms"] / 1000


def run_config_a(ticket: dict) -> dict:
    block = TICKET_BLOCK.format(**ticket)
    pred, cost, dur = call_agent("generalist.md", block)
    return {"severity": pred["severity"], "routing": pred["routing"],
            "cost_usd": cost, "latency_s": dur, "calls": 1}


def run_config_b(ticket: dict) -> dict:
    block = TICKET_BLOCK.format(**ticket)
    with ThreadPoolExecutor(max_workers=2) as pool:
        sev_f = pool.submit(call_agent, "severity.md", block)
        route_f = pool.submit(call_agent, "routing.md", block)
    sev, sev_cost, sev_dur = sev_f.result()
    route, route_cost, route_dur = route_f.result()
    return {"severity": sev["severity"], "routing": route["routing"],
            "cost_usd": sev_cost + route_cost, "latency_s": max(sev_dur, route_dur),
            "calls": 2}


def run_config_c(ticket: dict) -> dict:
    block = TICKET_BLOCK.format(**ticket)
    first, first_cost, first_dur = call_agent("generalist.md", block)
    review_block = REVIEW_BLOCK.format(
        author_role=ticket["author_role"], text=ticket["text"],
        original=json.dumps(first),
    )
    final, qa_cost, qa_dur = call_agent("qa_reviewer.md", review_block)
    return {"severity": final["severity"], "routing": final["routing"],
            "first_severity": first["severity"], "first_routing": first["routing"],
            "overridden": bool(final.get("overridden")),
            "cost_usd": first_cost + qa_cost, "latency_s": first_dur + qa_dur,
            "calls": 2}


RUNNERS = {"A": run_config_a, "B": run_config_b, "C": run_config_c}


def main() -> None:
    config = sys.argv[1].upper() if len(sys.argv) > 1 else ""
    if config not in RUNNERS:
        sys.exit("usage: python3 bench.py A|B|C")

    subset = json.loads((ROOT / "data" / "subset.json").read_text())["ids"]
    subset_ids = set(subset)
    tickets = [json.loads(l) for l in (ROOT / "data" / "tickets.jsonl").open()
               if json.loads(l)["id"] in subset_ids]
    # A typo'd or repeated id would otherwise silently shrink the benchmark and every
    # per-ticket figure downstream would be over the wrong n.
    unknown = sorted(subset_ids - {t["id"] for t in tickets})
    dupes = sorted({i for i in subset if subset.count(i) > 1})
    if unknown or dupes:
        sys.exit(f"data/subset.json is bad — unknown ids: {unknown or 'none'}; duplicate ids: {dupes or 'none'}")
    out_path = ROOT / "results" / f"raw_{config}.jsonl"

    done = set()
    if out_path.exists():
        done = {json.loads(l)["id"] for l in out_path.open() if "error" not in json.loads(l)}
    remaining = [t for t in tickets if t["id"] not in done]
    print(f"Config {config}: {len(done)} done, {len(remaining)} remaining", file=sys.stderr)

    def worker(ticket):
        try:
            row = RUNNERS[config]({"author_role": ticket["author_role"], "text": ticket["text"]})
            return {"id": ticket["id"], **row}
        except Exception as exc:
            return {"id": ticket["id"], "error": str(exc)}

    start = time.time()
    mode = "a" if done else "w"
    with out_path.open(mode) as out, ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for row in pool.map(worker, remaining):
            out.write(json.dumps(row) + "\n")
            out.flush()
            status = row.get("severity", "ERROR")
            print(f"  {row['id']}: {status}", file=sys.stderr)
    print(f"Config {config} finished in {time.time() - start:.0f}s -> {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

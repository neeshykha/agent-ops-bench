# Agent Ops Bench

Does adding a second AI agent actually help? Measured.

Every "how do you manage agents" conversation eventually hits the same question: when is one agent enough, and when is orchestration worth its cost? Most answers are architecture opinions. This repo answers it the way a support operations manager would — run the configurations against the same labeled workload, and compare accuracy, cost, and latency like you'd compare staffing models.

The workload is support ticket triage (severity + team routing) for a multifamily IoT platform, reusing the labeled dataset and taxonomy from [claude-triage-simulator](https://github.com/neeshykha/claude-triage-simulator). The benchmark runs a hard-case-weighted 30-ticket subset — every edge-case group from the source dataset plus a stratified sample — so config differences show where triage is actually hard.

## The three configurations

| | Pattern | Calls/ticket | The staffing analogy |
|---|---|---|---|
| **A** | Generalist | 1 | One experienced agent handles the whole ticket |
| **B** | Specialists | 2 (parallel) | Separate severity assessor and routing dispatcher, each with only their slice of the playbook |
| **C** | Generalist + QA | 2 (sequential) | Same generalist, plus an independent reviewer who audits every call and can override |

Config C is the pattern support teams already know: it's QA sampling, applied to an AI worker instead of a human one. The reviewer's prompt includes explicit audit discipline — override only with a rule-based reason, because agreement bias and second-guessing are both real failure modes.

## Results

| Config | Severity | Routing | P1 catch | Cost/ticket | Avg latency |
|---|---|---|---|---|---|
| Generalist | 70% | 83% | 6/7 | $0.080 | 5.1s |
| Specialists | 70% | **97%** | 7/7 | $0.149 | 5.2s |
| Generalist + QA | **80%** | 90% | 7/7 | $0.160 | 10.4s |

(Accuracy numbers are on the deliberately hard subset — the same generalist scores 75%/87% on the full dataset. Full per-miss breakdown: [`results/scorecard.md`](results/scorecard.md).)

Three findings that generalize:

**1. Specialization fixed the mechanical dimension, not the judgment one.** Giving routing its own agent with a narrower prompt took routing from 83% to 97% — but a dedicated severity specialist didn't move severity accuracy at all. Routing is mostly clean category boundaries; severity requires weighing context (is the lockout *still happening*? does "the whole floor" change the scope?). Splitting the task helps where the subtask is crisp, and does nothing where the subtask is the hard part.

**2. The QA reviewer earned its cost — on exactly the failure modes you'd predict.** The reviewer issued 9 overrides: 6 fixed real first-pass errors, 2 broke correct calls, for +4 net corrections at $0.60 per net correction. What it caught is the notable part: both "resolved lockout still classified urgent" tickets (the documented weak spot from the source project's eval), and one under-triaged P1 — a resident locked out of every entry method for 36 hours that the first pass called a P2. In triage, a missed P1 is the failure that matters; a reviewer that catches those pays for itself at almost any price.

**3. Nothing is free — the costs just land in different budgets.** Specialists double cost but not latency (parallel calls). The QA reviewer doubles both cost and latency (sequential by design — it needs the first answer). If your triage queue is latency-sensitive, the reviewer belongs on a sampled subset or async re-check, not inline on every ticket. That's a deployment decision, not an architecture decision.

## The ops takeaway

Choosing an agent pattern is a staffing decision. The generalist is your baseline headcount. Specialists are worth it when a subtask has crisp boundaries and its error rate is the problem. A QA layer is worth it when the cost of a missed critical is high — which in support triage, it always is. And the only way to know any of this is to measure against a labeled workload, which is the part most agent architecture discussions skip.

## Repo structure

```
prompts/            # One explicit prompt file per agent role
  generalist.md     # Full taxonomy
  severity.md       # Severity slice only
  routing.md        # Routing slice only
  qa_reviewer.md    # Full taxonomy + audit discipline
data/tickets.jsonl  # 60 labeled synthetic tickets (from claude-triage-simulator)
data/subset.json    # The 30-ticket hard-case-weighted benchmark subset
bench.py            # Runs one config over the subset (parallel worker pool)
score.py            # Comparison scorecard + QA reviewer economics
results/scorecard.md
```

A deliberate design note: this repo has no CLAUDE.md driving classification. Each agent's prompt is an explicit file, because config B's specialists must NOT see the full taxonomy — an auto-loaded instruction file would leak context to every agent. Controlling exactly what each agent sees is half of what "managing agents" means.

## Running it

```bash
# Requires the Claude Code CLI, authenticated
python3 bench.py A   # ~30 calls
python3 bench.py B   # ~60 calls
python3 bench.py C   # ~60 calls
python3 score.py     # writes results/scorecard.md
```

Runs are resumable — re-running a config skips tickets already completed. Cost and latency per call are captured from the CLI's JSON envelope, so the economics in the scorecard are measured, not estimated.

## Tech stack

- **Claude Code CLI** — agent execution (Sonnet)
- **Python stdlib only** — orchestration, worker pool, scoring

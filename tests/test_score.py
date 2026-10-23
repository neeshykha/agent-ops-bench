"""Tests for score.py. Runs the scorer against a temp copy of the repo layout so the
committed results/scorecard.md is never touched."""

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import score  # noqa: E402


def write_jsonl(path: Path, rows: list) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


class ScoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        (self.tmp / "results").mkdir()
        shutil.copy(REPO / "data" / "tickets.jsonl", self.tmp / "data")
        shutil.copy(REPO / "data" / "subset.json", self.tmp / "data")
        self.scorecard = self.tmp / "results" / "scorecard.md"
        self._root = score.ROOT
        score.ROOT = self.tmp

    def tearDown(self):
        score.ROOT = self._root
        shutil.rmtree(self.tmp)

    def run_score(self) -> str:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            score.main()
        return out.getvalue()

    def test_no_raw_results_leaves_committed_scorecard_alone(self):
        # A fresh clone has results/scorecard.md but no results/raw_*.jsonl (gitignored).
        committed = "# committed scorecard — must survive\n"
        self.scorecard.write_text(committed)
        with self.assertRaises(SystemExit):
            self.run_score()
        self.assertEqual(self.scorecard.read_text(), committed)

    def test_all_error_raw_file_is_skipped_not_crashed(self):
        # bench.py records a failed ticket as {"id": ..., "error": ...}; a run where every
        # ticket failed must not take the whole scorecard down with a ZeroDivisionError.
        write_jsonl(self.tmp / "results" / "raw_A.jsonl",
                    [{"id": "T003", "error": "claude CLI exited 1: boom"}])
        write_jsonl(self.tmp / "results" / "raw_B.jsonl",
                    [{"id": "T003", "severity": "P1", "routing": "Environmental Monitoring",
                      "cost_usd": 0.1, "latency_s": 5.0, "calls": 2}])
        report = self.run_score()
        self.assertNotIn("Generalist (1 call)", report)
        self.assertIn("| Specialists (2 calls) | 1/1 (100%) | 1/1 (100%) | 1/1 | 0 | $0.100 | 5.0s |", report)

    def test_qa_reviewer_economics_arithmetic(self):
        # Pins the definitions behind the headline: an override is any change from the first
        # pass; a catch takes a ticket from wrong to fully right; a harm is the reverse; an
        # override that leaves the ticket wrong is neither; cost per net correction is the
        # added cost over config A, times tickets, over (catches - harms).
        def a(pid, sev, route):
            return {"id": pid, "severity": sev, "routing": route, "cost_usd": 0.08, "latency_s": 5.0, "calls": 1}

        def c(pid, first, final):
            return {"id": pid, "first_severity": first[0], "first_routing": first[1],
                    "severity": final[0], "routing": final[1], "overridden": first != final,
                    "cost_usd": 0.16, "latency_s": 10.0, "calls": 2}

        em, bill, t1, fs, acs = ("Environmental Monitoring", "Billing & Account Management",
                                 "Tier 1 Support", "Field Service / Hardware Dispatch",
                                 "Access Control & Security")
        write_jsonl(self.tmp / "results" / "raw_A.jsonl",
                    [a("T003", "P1", em), a("T045", "P4", bill), a("T035", "P4", t1),
                     a("T012", "P2", fs), a("T011", "P2", acs)])
        write_jsonl(self.tmp / "results" / "raw_C.jsonl", [
            c("T003", ("P2", em), ("P1", em)),      # catch: wrong -> right
            c("T045", ("P4", bill), ("P3", bill)),  # harm: right -> wrong
            c("T035", ("P3", t1), ("P4", t1)),      # catch
            c("T012", ("P3", fs), ("P1", fs)),      # override, still wrong: neither
            c("T011", ("P2", acs), ("P2", acs)),    # confirmed, no override
        ])
        report = self.run_score()
        self.assertIn("- Overrides issued: 4/5", report)
        self.assertIn("- Catches (fixed a first-pass error): 2 — T003, T035", report)
        self.assertIn("- Harms (broke a correct first-pass call): 1 — T045", report)
        self.assertIn("- Added cost vs. Config A: $0.080/ticket", report)
        self.assertIn("- Net corrections: +1 — reviewer cost per net correction: $0.40", report)


if __name__ == "__main__":
    unittest.main()

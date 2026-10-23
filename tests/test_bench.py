"""Tests for bench.py's run setup. The agent call is stubbed out — nothing here
touches the Claude CLI."""

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import bench  # noqa: E402


def fake_runner(ticket: dict) -> dict:
    return {"severity": "P4", "routing": "Tier 1 Support", "cost_usd": 0.0, "latency_s": 0.0, "calls": 1}


class BenchSubsetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data").mkdir()
        (self.tmp / "results").mkdir()
        shutil.copy(REPO / "data" / "tickets.jsonl", self.tmp / "data")
        self.raw = self.tmp / "results" / "raw_A.jsonl"
        self._saved = (bench.ROOT, bench.RUNNERS, sys.argv)
        bench.ROOT = self.tmp
        bench.RUNNERS = {"A": fake_runner}
        sys.argv = ["bench.py", "A"]

    def tearDown(self):
        bench.ROOT, bench.RUNNERS, sys.argv = self._saved
        shutil.rmtree(self.tmp)

    def set_subset(self, ids: list) -> None:
        (self.tmp / "data" / "subset.json").write_text(json.dumps({"ids": ids}))

    def run_bench(self) -> None:
        with redirect_stderr(io.StringIO()):
            bench.main()

    def test_unknown_subset_id_is_an_error_not_a_silent_skip(self):
        # A typo in subset.json used to silently shrink the benchmark: the id was dropped
        # and the run reported as complete, with every per-ticket stat over the wrong n.
        self.set_subset(["T001", "T999"])
        with self.assertRaises(SystemExit) as cm:
            self.run_bench()
        self.assertIn("T999", str(cm.exception))
        self.assertFalse(self.raw.exists(), "no run should start on a bad subset")

    def test_duplicate_subset_id_is_an_error(self):
        self.set_subset(["T001", "T001"])
        with self.assertRaises(SystemExit) as cm:
            self.run_bench()
        self.assertIn("T001", str(cm.exception))
        self.assertFalse(self.raw.exists())

    def test_valid_subset_runs_every_ticket(self):
        self.set_subset(["T001", "T002"])
        self.run_bench()
        rows = [json.loads(l) for l in self.raw.read_text().splitlines()]
        self.assertEqual([r["id"] for r in rows], ["T001", "T002"])


if __name__ == "__main__":
    unittest.main()

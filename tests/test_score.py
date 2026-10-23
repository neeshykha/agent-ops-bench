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


if __name__ == "__main__":
    unittest.main()

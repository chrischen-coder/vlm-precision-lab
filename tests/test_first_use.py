"""First CLI failures and replay outputs must be recoverable without data loss."""

import json
import subprocess
import sys

import pytest

from precisionlab.metrics import compare
from precisionlab.report import render


def result():
    sample = {"id": "one", "group_id": "document", "task": "number", "image": "one.png",
              "prompt": "Read the number", "answer": "4"}
    prediction = {"id": "one", "prediction": "4", "input_sha256": "same"}
    return compare([sample], [prediction], [prediction])


@pytest.mark.parametrize("existing", ["report.html", "report.json"])
def test_replay_never_replaces_either_existing_report(tmp_path, existing):
    saved = tmp_path / existing
    saved.write_text("previous run")
    with pytest.raises(FileExistsError):
        render(result(), tmp_path / "report.html")
    assert saved.read_text() == "previous run"
    assert sorted(p.name for p in tmp_path.iterdir()) == [existing]


def test_json_report_path_cannot_overwrite_its_html(tmp_path):
    with pytest.raises(ValueError, match="HTML output path"):
        render(result(), tmp_path / "report.json")
    assert not list(tmp_path.iterdir())
    render(result(), tmp_path / "report.html")
    assert (tmp_path / "report.html").read_text().startswith("<!doctype html>")
    assert json.loads((tmp_path / "report.json").read_text())["overall"]["reference_em"] == 1


@pytest.mark.parametrize("contents", [None, "{bad json}\n"])
def test_cli_input_failure_is_a_short_error_and_nonzero_exit(tmp_path, contents):
    source = tmp_path / "input.jsonl"
    if contents is not None:
        source.write_text(contents)
    run = subprocess.run([sys.executable, "-m", "precisionlab.cli", "evaluate",
        "--dataset", str(source), "--endpoint", "http://127.0.0.1:1/v1", "--model", "unused",
        "--output", str(tmp_path / "run")], text=True, capture_output=True)
    assert run.returncode == 2
    assert run.stdout == ""
    assert "precisionlab:" in run.stderr
    assert "Traceback" not in run.stderr
    assert not (tmp_path / "run").exists()

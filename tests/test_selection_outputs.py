"""Selections and recipe decisions must preserve inputs and previous evidence."""

import json
from pathlib import Path

from PIL import Image
import pytest

from precisionlab import cli
from precisionlab.data import fingerprint, load_samples


@pytest.fixture
def inputs(tmp_path):
    Image.new("RGB", (2, 2), "white").save(tmp_path / "one.png")
    rows = [{"id": str(i), "group_id": "document", "split": "calibration", "task": "ocr",
             "image": "one.png", "prompt": "Read the number", "answer": "4", "features": ["plain"]}
            for i in range(2)]
    files = {name: tmp_path / name for name in ("dataset.jsonl", "costs.json", "candidates.json", "constraints.json")}
    files["dataset.jsonl"].write_text("".join(json.dumps(row) + "\n" for row in rows))
    files["costs.json"].write_text(json.dumps({"0": 1, "1": 1}))
    files["candidates.json"].write_text(json.dumps([{"name": "verified", "weight_bytes": 100,
        "task_em": {"ocr": 1.0}, "export_reload_verified": True}]))
    files["constraints.json"].write_text(json.dumps({"max_weight_bytes": 200, "min_task_em": {"ocr": 0.9}}))
    return files


def arguments(command, files, output):
    if command == "choose":
        return [command, "--candidates", str(files["candidates.json"]),
                "--constraints", str(files["constraints.json"]), "--output", str(output)]
    return [command, "--dataset", str(files["dataset.jsonl"]), "--costs", str(files["costs.json"]),
            "--budget", "1", "--output", str(output)]


def snapshot(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("command,target", [
    ("choose", "candidates.json"), ("choose", "constraints.json"), ("choose", "previous.json"),
    ("select", "dataset.jsonl"), ("select", "costs.json"), ("select", "previous.jsonl"),
    ("select", "sidecar"), ("select", "sidecar-dataset.jsonl"), ("select", "sidecar-costs.json"),
])
def test_conflicting_output_preserves_all_inputs_and_results(tmp_path, inputs, capsys, command, target):
    output = tmp_path / "picked.jsonl"
    if target.startswith("sidecar"):
        saved = output.with_suffix(".selection.json")
        if target == "sidecar":
            saved.write_text("previous selection metadata\n")
        else:
            key = target.removeprefix("sidecar-")
            inputs[key].rename(saved)
            inputs[key] = saved
    else:
        output = inputs.get(target, tmp_path / target)
        if target.startswith("previous"):
            output.write_text("previous result\n")
    before = snapshot(tmp_path)
    assert cli.main(arguments(command, inputs, output)) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Choose a new output path" in captured.err
    assert "Traceback" not in captured.err
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("command,sidecar", [("choose", False), ("select", False), ("select", True)])
@pytest.mark.parametrize("kind", ["symlink", "hardlink", "dangling-symlink", "directory"])
def test_output_aliases_and_directories_are_never_replaced(tmp_path, inputs, capsys, command, sidecar, kind):
    output = tmp_path / "result.jsonl"
    destination = output.with_suffix(".selection.json") if sidecar else output
    source = inputs["candidates.json" if command == "choose" else "costs.json"]
    if kind == "symlink":
        destination.symlink_to(source)
    elif kind == "hardlink":
        destination.hardlink_to(source)
    elif kind == "dangling-symlink":
        destination.symlink_to(tmp_path / "missing.json")
    else:
        destination.mkdir()
    before = snapshot(tmp_path)
    assert cli.main(arguments(command, inputs, output)) == 2
    assert "Choose a new output path" in capsys.readouterr().err
    assert snapshot(tmp_path) == before
    assert destination.is_symlink() if "symlink" in kind else destination.exists()
    if sidecar:
        assert not output.exists()
    assert not (tmp_path / "missing.json").exists()


@pytest.mark.parametrize("command", ["select", "choose"])
def test_new_directory_succeeds_and_repeat_can_recover_with_new_path(tmp_path, inputs, capsys, command):
    source_snapshot = snapshot(tmp_path)
    output = tmp_path / "new results" / "run 1" / ("picked.jsonl" if command == "select" else "decision.json")
    assert cli.main(arguments(command, inputs, output)) == 0
    capsys.readouterr()
    if command == "select":
        selected = [json.loads(line) for line in output.read_text().splitlines()]
        stats = json.loads(output.with_suffix(".selection.json").read_text())
        assert len(selected) == stats["samples"] == 1
        assert stats["spent_tokens"] == 1
        assert stats["dataset_sha256"] == fingerprint(load_samples(inputs["dataset.jsonl"]), inputs["dataset.jsonl"])
    else:
        assert json.loads(output.read_text())["winner"]["name"] == "verified"
    first_run = snapshot(tmp_path)
    assert cli.main(arguments(command, inputs, output)) == 2
    assert "Choose a new output path" in capsys.readouterr().err
    assert snapshot(tmp_path) == first_run
    retry = output.parent.parent / "run 2" / output.name
    assert cli.main(arguments(command, inputs, retry)) == 0
    assert retry.read_bytes() == output.read_bytes()
    assert all((tmp_path / name).read_bytes() == data for name, data in source_snapshot.items())


def test_sidecar_created_after_preflight_does_not_leave_partial_selection(tmp_path, inputs, monkeypatch, capsys):
    output = tmp_path / "picked.jsonl"
    metadata = output.with_suffix(".selection.json")
    original_open = Path.open

    def create_conflict(path, mode="r", *args, **kwargs):
        if path == metadata and mode == "x":
            assert output.read_bytes() == b""
            with original_open(path, "w") as stream:
                stream.write("another run's metadata\n")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", create_conflict)
    assert cli.main(arguments("select", inputs, output)) == 2
    assert "Choose a new output path" in capsys.readouterr().err
    assert not output.exists()
    assert metadata.read_text() == "another run's metadata\n"


def test_fingerprint_failure_happens_before_any_selection_is_written(tmp_path, inputs, monkeypatch, capsys):
    output = tmp_path / "new results" / "picked.jsonl"

    def missing_image(*args):
        raise FileNotFoundError("image removed before fingerprinting")

    monkeypatch.setattr(cli, "fingerprint", missing_image)
    assert cli.main(arguments("select", inputs, output)) == 2
    assert "image removed" in capsys.readouterr().err
    assert not output.parent.exists()

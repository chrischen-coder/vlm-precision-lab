"""Run the shipped tests against the shipped source, outside the checkout."""

import os
import re
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


root = Path(__file__).resolve().parents[1]
# Match this checkout's release version, never a stale artifact in dist/.
release = re.search(r'^version = "([^"\n]+)"$', (root / "pyproject.toml").read_text(), re.MULTILINE)
if release is None:
    raise SystemExit("Expected a static project version")
archive = root / "dist" / ("vlm_precision_lab-" + release[1] + ".tar.gz")
with tempfile.TemporaryDirectory(prefix="sdist-check-") as folder:
    destination = Path(folder)
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            if not (member.isfile() or member.isdir()) or not (destination / member.name).resolve().is_relative_to(destination.resolve()):
                raise ValueError("Unexpected source archive entry")
        source.extractall(destination, **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
    checkout, = destination.iterdir()
    env = {**os.environ, "PYTHONPATH": str(checkout / "src")}
    command = [sys.executable, "-m", "pytest", "-q"]
    subprocess.run(command, cwd=checkout, env=env, check=True)
print(f"Verified bundled tests and source: {archive.name}")

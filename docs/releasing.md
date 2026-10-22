# Release 0.3.0

Distribution: GitHub Release, with a wheel, source distribution and SHA-256 checksums. No package-registry upload is required. Use a new tag; never replace an existing release. Keep pyproject.toml and the package's __version__ consistent.

Build from the final clean commit after its pull request has merged and CI has passed:

```sh
python -m pip install build
python -m pytest -q
python -m build
python tools/check_sdist.py
```

The assets for this version are `dist/vlm_precision_lab-0.3.0-py3-none-any.whl` and `dist/vlm_precision_lab-0.3.0.tar.gz`. Generate `SHA256SUMS` for those two files, install the wheel into a fresh environment, and check the installed version and CLI before uploading. Select these exact names so older build files are not included accidentally.

Users can install the tagged source with:

```sh
python -m pip install git+https://github.com/crown-sports/vlm-precision-lab.git@v0.3.0
```

The release notes should use this version's CHANGELOG entry and retain the documented limits of the evidence; offline tests do not establish production-network, downstream model-quality or GPU-performance results.

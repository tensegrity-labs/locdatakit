# locdatakit

A Python toolkit and CLI for processing, analyzing, and reporting on location data.

⚠️ This is in early-stage development. Expect API and config changes in future versions.

## What It Does

- Loads one GPX file, a directory, or a glob of GPX files
- Applies the current prototype trip separation heuristics
- Writes a CSV report with trip start/end, distance, duration, and speed stats
- Optionally labels trip endpoints using a local places file

## Quickstart

Install from PyPI:

```bash
pip install locdatakit
locdatakit --help
```

Install with optional HERE SDK support:

```bash
pip install "locdatakit[here]"
```

Run on your GPX file:

```bash
locdatakit trip-log --gpx /path/to/file-or-glob.gpx
```

Install from source (development):

```bash
git clone https://github.com/tensegrity-labs/locdatakit.git
cd locdatakit
pip install -e .[dev]
locdatakit trip-log --gpx examples/example.gpx --places examples/places.yaml
```

If the package is not published yet, use the source install flow above.
After publishing to PyPI, prefer `pip install locdatakit` (or `pip install "locdatakit[here]"` for HERE support).

## CLI

See help for usage
```bash
locdatakit --help
locdatakit <command> --help
```

If `--out` is omitted, output defaults to CSV and is written next to the input source:

- file input: `<input_stem>_trip_log.csv`
- directory/glob input: `trip_log.csv` in the source directory

## Dependency Notes

Current runtime dependencies are: `click`, `gpxpy`, `pint`, `geopy`, `scipy`, `pytz`, and `PyYAML`.

HERE lookup is optional and disabled by default.

## Optional HERE Lookup

To enable remote lookup of unknown places, pass `--here`.
The HERE Python SDK manages credentials/configuration (including config-file based setup).
If initialization fails, the CLI shows an error with setup docs:

- https://www.here.com/docs/bundle/data-sdk-for-python-developer-guide-v2/page/topics/credentials.html

CI/tests do not require HERE credentials.

## Known Limitations

- Trip segmentation heuristics are prototype-quality and may over/under-segment in some data sets.
- CSV schema and CLI flags are expected to evolve in upcoming releases.

## Contributing

Set up a dev environment:

```bash
pip install -e .[dev]
```

Run tests:

```bash
pytest -q
```

Bump version with `bump-my-version`:

```bash
# patch: 0.0.1 -> 0.0.2
bump-my-version bump patch

# minor: 0.0.1 -> 0.1.0
bump-my-version bump minor

# major: 0.0.1 -> 1.0.0
bump-my-version bump major
```

The bump command updates both `pyproject.toml` and `locdatakit/__init__.py`.

General contribution guidelines:

- Keep changes focused and scoped to a single concern when possible.
- Add or update tests for behavior changes.
- Keep CLI behavior backward compatible unless a breaking change is documented.
- Avoid committing personal data (real GPX traces, real addresses, API keys, credential files).
- Use synthetic/redacted data in examples, tests, and issue discussions.

Before opening a PR:

- Run tests locally: `pytest -q`
- Run a build check: `python -m build`
- Update docs/changelog when user-facing behavior changes

## Filing Issues

When filing an issue, include:

- What you expected to happen
- What happened instead (full error output if possible)
- Exact command used
- OS and Python version
- `locdatakit` version (`locdatakit --version`)
- Whether `--here` was enabled

If relevant, include a minimal reproducible input (synthetic GPX/places file preferred).
Do not share private location data, API keys, or credential files in issues.

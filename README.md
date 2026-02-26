# locdatakit

A Python toolkit and cli for processing, analyzing, and reporting on location data.

⚠️ This is an early-stage `v0.0.1` release. Expect API and config changes in future versions.

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

## Known Limitations (v0.0.1)

- Trip segmentation heuristics are prototype-quality and may over/under-segment in some data sets.
- CSV schema and CLI flags are expected to evolve in upcoming releases.

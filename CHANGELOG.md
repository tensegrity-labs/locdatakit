# Changelog

## 0.0.1 - 2026-02-26

- Added Python packaging scaffold with `pyproject.toml`
- Added installable Click CLI: `locdatakit`
- Renamed primary command to `trip-log` and added `--report-type auto|csv`
- Made `--out` optional with derived default CSV path next to input data
- Ported prototype GPX logic into package module `locdatakit.gpxtools`
- Added optional places loading from YAML and Home Assistant zones JSON
- Added synthetic examples (`examples/`)
- Added minimal pytest coverage for places loaders and CLI CSV output
- Added release docs updates in `README.md`

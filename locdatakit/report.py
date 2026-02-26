from __future__ import annotations

from pathlib import Path

from .gpxtools import GpxTools


def write_trip_report_csv(
    gpxtools: GpxTools,
    output_csv: str,
    *,
    units: str,
    tz_name: str | None,
    lookup_addr: bool,
) -> int:
    out_path = Path(output_csv).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as csvfile:
        csvfile.write(gpxtools.get_csv_header(units))
        csvfile.write("\n")
        for trip in gpxtools.trips:
            row = gpxtools.get_csv_str(trip, lookup_addr=lookup_addr, units=units, tz_name=tz_name)
            if row:
                csvfile.write(row)
                csvfile.write("\n")
    return len(gpxtools.trips)

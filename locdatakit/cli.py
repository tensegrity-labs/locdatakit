from __future__ import annotations

from pathlib import Path

import click

from . import __version__
from .gpxtools import GpxTools, resolve_gpx_paths
from .places import load_places
from .report import write_trip_report_csv


def _map_units(units: str) -> str:
    return "imperial" if units == "miles" else "metric_km"


def _derive_default_output_path(gpx_input: str, gpx_paths: list[str]) -> str:
    input_path = Path(gpx_input).expanduser()
    if input_path.exists() and input_path.is_file():
        return str(input_path.with_name(f"{input_path.stem}_trip_log.csv").resolve())
    if input_path.exists() and input_path.is_dir():
        return str((input_path / "trip_log.csv").resolve())
    if len(gpx_paths) == 1:
        single = Path(gpx_paths[0])
        return str(single.with_name(f"{single.stem}_trip_log.csv").resolve())
    common_parent = Path(gpx_paths[0]).parent
    return str((common_parent / "trip_log.csv").resolve())


def _resolve_report_type(report_type: str, output_path: str) -> str:
    if report_type != "auto":
        return report_type
    ext = Path(output_path).suffix.lower()
    if ext == ".csv" or not ext:
        return "csv"
    raise click.ClickException(
        f"Unable to infer report type from extension '{ext}'. "
        "Use --report-type csv or provide a .csv output path."
    )


@click.group()
@click.version_option(version=__version__, prog_name="locdatakit")
def cli() -> None:
    """Tooling for GPX location logs."""


@cli.command(name="trip-log")
@click.option("--gpx", "gpx_input", required=True, help="GPX file path, directory, or glob pattern.")
@click.option("--out", "output_path", default=None, help="Output report path. Defaults to a derived CSV path.")
@click.option(
    "--report-type",
    type=click.Choice(["auto", "csv"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Report format. 'auto' infers from --out extension.",
)
@click.option("--tz", "timezone_name", default="US/Mountain", show_default=True, help="IANA timezone name.")
@click.option("--units", type=click.Choice(["miles", "km"], case_sensitive=False), default="miles", show_default=True)
@click.option("--places", "places_file", default=None, help="Places file (.yaml/.yml or Home Assistant zones .json).")
@click.option("--here", "use_here", is_flag=True, default=False, help="Enable HERE API lookups for unknown places.")
@click.option("--dry-run", is_flag=True, default=False, help="Parse input and show trip count without writing output.")
def trip_log(
    gpx_input: str,
    output_path: str | None,
    report_type: str,
    timezone_name: str,
    units: str,
    places_file: str | None,
    use_here: bool,
    dry_run: bool,
) -> None:
    """Generate a trip log report from GPX input."""
    gpx_paths = resolve_gpx_paths(gpx_input)
    if not gpx_paths:
        raise click.ClickException(f"No GPX files found for input: {gpx_input}")

    resolved_output_path = output_path or _derive_default_output_path(gpx_input, gpx_paths)
    resolved_report_type = _resolve_report_type(report_type.lower(), resolved_output_path)

    # TODO: Add a guided command to validate/generate HERE SDK credentials config.

    gpxtools = GpxTools(min_distance_km=1.0, min_ave_speed_kmh=5.0, lookup_tolerance_m=80, here_enabled=use_here)

    if places_file:
        places = load_places(places_file)
        gpxtools.load_known_places([place.to_lookup_record() for place in places])

    gpxtools.load_trips(gpx_paths)
    click.echo(f"Trips found: {len(gpxtools.trips)}")

    if dry_run:
        click.echo("Dry run complete. No CSV written.")
        return

    if resolved_report_type != "csv":
        raise click.ClickException(f"Unsupported report type: {resolved_report_type}")

    rows = write_trip_report_csv(gpxtools, resolved_output_path, units=_map_units(units.lower()), tz_name=timezone_name, lookup_addr=use_here)
    click.echo(f"Wrote {rows} trips to: {resolved_output_path}")

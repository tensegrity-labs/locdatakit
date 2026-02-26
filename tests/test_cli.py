import shutil
from pathlib import Path

from click.testing import CliRunner

from locdatakit.cli import cli


def test_cli_trip_log_generates_csv(tmp_path):
    out_csv = tmp_path / "out.csv"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "trip-log",
            "--gpx",
            "examples/example.gpx",
            "--out",
            str(out_csv),
            "--places",
            "examples/places.yaml",
            "--tz",
            "UTC",
            "--units",
            "km",
        ],
    )

    assert result.exit_code == 0, result.output
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8").splitlines()
    assert len(content) >= 2
    assert "Start Date" in content[0]
    assert "End Address" in content[0]


def test_cli_trip_log_defaults_output_next_to_input():
    src = Path("examples/example.gpx")
    test_gpx = Path("examples/example_copy.gpx")
    shutil.copyfile(src, test_gpx)

    runner = CliRunner()
    expected_out = Path("examples/example_copy_trip_log.csv")
    try:
        result = runner.invoke(
            cli,
            [
                "trip-log",
                "--gpx",
                str(test_gpx),
            ],
        )
        assert result.exit_code == 0, result.output
        assert expected_out.exists()
    finally:
        if test_gpx.exists():
            test_gpx.unlink()
        if expected_out.exists():
            expected_out.unlink()

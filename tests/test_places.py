import shutil
from pathlib import Path

from locdatakit.places import load_places, load_places_ha_json, load_places_yaml


def test_load_places_yaml():
    places = load_places_yaml("examples/places.yaml")
    assert len(places) == 2
    assert places[0].id == "home"
    assert places[1].name == "Office"
    assert "icon:mdi:briefcase" in (places[1].tags or [])


def test_load_places_ha_json():
    places = load_places_ha_json("examples/zones.json")
    assert len(places) == 2
    assert places[0].id == "home"
    assert "icon:mdi:home" in (places[0].tags or [])


def test_load_places_extensionless_json():
    src = Path("examples/zones.json")
    dst = Path("examples/zone")
    shutil.copyfile(src, dst)
    try:
        places = load_places(str(dst))
        assert len(places) == 2
        assert places[1].id == "office"
    finally:
        if dst.exists():
            dst.unlink()

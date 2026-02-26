from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Place:
    id: str
    name: str
    lat: float
    lon: float
    radius_m: float = 100.0
    tags: list[str] | None = None

    def to_lookup_record(self) -> dict[str, Any]:
        tag_list = self.tags or []
        icon_tag = next((tag for tag in tag_list if tag.startswith("icon:")), "Unknown")
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.lat,
            "longitude": self.lon,
            "radius": self.radius_m,
            "icon": icon_tag,
            "tags": tag_list,
        }


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_places(path: str) -> list[Place]:
    src = Path(path)
    suffix = src.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return load_places_yaml(path)
    if suffix == ".json":
        return load_places_ha_json(path)

    # Support extensionless files (for example Home Assistant `zone` exports).
    try:
        return load_places_ha_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    try:
        return load_places_yaml(path)
    except yaml.YAMLError:
        pass

    raise ValueError(f"Unsupported places format: {path}")


def load_places_yaml(path: str) -> list[Place]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw_places = data.get("places", data if isinstance(data, list) else [])
    places: list[Place] = []
    for idx, item in enumerate(raw_places):
        place = Place(
            id=str(item.get("id", f"place_{idx}")),
            name=str(item.get("name", f"Place {idx}")),
            lat=_as_float(item.get("lat"), 0.0),
            lon=_as_float(item.get("lon"), 0.0),
            radius_m=_as_float(item.get("radius_m", item.get("radius", 100.0)), 100.0),
            tags=[str(tag) for tag in (item.get("tags") or [])],
        )
        places.append(place)
    return places


def load_places_ha_json(path: str) -> list[Place]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        raw_items = data["data"].get("items", [])
    elif isinstance(data, list):
        raw_items = data
    else:
        raw_items = []

    places: list[Place] = []
    for idx, item in enumerate(raw_items):
        icon = item.get("icon")
        tags = [f"icon:{icon}"] if icon else []
        places.append(
            Place(
                id=str(item.get("id", f"zone_{idx}")),
                name=str(item.get("name", f"Zone {idx}")),
                lat=_as_float(item.get("latitude"), 0.0),
                lon=_as_float(item.get("longitude"), 0.0),
                radius_m=_as_float(item.get("radius", 100.0), 100.0),
                tags=tags,
            )
        )
    return places

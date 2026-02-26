from __future__ import annotations

import glob
import json
import math
import os
from copy import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import gpxpy
import pint
import pytz
from geopy import distance as geopy_distance
from scipy.spatial import distance

try:
    from here.platform import Platform as HereLegacyPlatform
except Exception:  # pragma: no cover - optional dependency
    HereLegacyPlatform = None

try:
    from here_location_services import LS as HereLS
except Exception:  # pragma: no cover - optional dependency
    HereLS = None


UNITS = pint.UnitRegistry()


@lru_cache(maxsize=10000)
def geopy_distance_km(coord_a: tuple[float, float], coord_b: tuple[float, float]) -> float:
    return geopy_distance.distance(coord_a, coord_b)._Distance__kilometers


def resolve_gpx_paths(gpx_input: str) -> list[str]:
    """Resolve a file, directory, or glob into GPX file paths."""
    expanded = os.path.expanduser(gpx_input)
    matches = sorted(glob.glob(expanded))
    if matches:
        files: list[str] = []
        for match in matches:
            if os.path.isdir(match):
                files.extend(sorted(glob.glob(os.path.join(match, "**", "*.gpx"), recursive=True)))
            elif match.lower().endswith(".gpx"):
                files.append(match)
        return [str(Path(path).resolve()) for path in files]

    if os.path.isdir(expanded):
        files = sorted(glob.glob(os.path.join(expanded, "**", "*.gpx"), recursive=True))
        return [str(Path(path).resolve()) for path in files]
    if os.path.isfile(expanded):
        return [str(Path(expanded).resolve())]
    return []


@dataclass
class RunConfig:
    min_distance_km: float = 1.0
    min_ave_speed_kmh: float = 5.0
    lookup_tolerance_m: float = 80.0
    timezone_name: str = "US/Mountain"
    units: str = "imperial"
    lookup_here: bool = False


class GpxLookup:
    def __init__(self, lookup_tolerance_m: float = 10, here_enabled: bool = False) -> None:
        self.lookup_tolerance_m = lookup_tolerance_m
        self.known_addresses: list[dict] | None = None
        self.here_enabled = here_enabled
        self.here_api = None
        self.here_mode = None
        self.discover_service = None
        self.revgeocode_service = None
        self.geocode_service = None

    def init_here_api(self) -> None:
        if not self.here_enabled:
            raise RuntimeError("HERE lookup is disabled. Use --here to enable it.")
        if HereLegacyPlatform is None and HereLS is None:
            raise RuntimeError(
                "HERE SDK is not installed. Install optional dependency: pip install 'locdatakit[here]'."
            )
        if not self.here_api:
            try:
                if HereLegacyPlatform is not None:
                    self.here_mode = "legacy"
                    self.here_api = HereLegacyPlatform()
                    self.discover_service = self.here_api.get_service("hrn:here:service::olp-here:search-discover-7")
                    self.revgeocode_service = self.here_api.get_service("hrn:here:service::olp-here:search-revgeocode-7")
                    self.geocode_service = self.here_api.get_service("hrn:here:service::olp-here:search-geocode-7")
                else:
                    self.here_mode = "hls"
                    self.here_api = HereLS()
            except Exception as exc:
                raise RuntimeError(
                    "Unable to initialize HERE SDK credentials/config. "
                    "See: https://www.here.com/docs/bundle/data-sdk-for-python-developer-guide-v2/page/topics/credentials.html"
                ) from exc

    def load_known_addresses(self, file_path: str) -> None:
        with open(file_path, "r", encoding="utf-8") as json_file:
            file_data = json.load(json_file)
        addr_data = file_data.get("data") if isinstance(file_data, dict) else None
        self.known_addresses = addr_data.get("items") if addr_data else file_data

    def load_known_places(self, places: Iterable[dict]) -> None:
        self.known_addresses = list(places)

    def lookup_address(self, coord: tuple[float, float]) -> tuple[str, str]:
        self.init_here_api()
        lat, lon = coord
        if self.here_mode == "legacy":
            reply = self.revgeocode_service.get("/revgeocode", {"at": f"{lat},{lon}"})
            items = reply.get("items") or []
            addr_str = items[0].get("title") if items else "Unknown"
        else:
            reply = self.here_api.reverse_geocode(lat=lat, lng=lon, limit=1)
            items = getattr(reply, "items", []) or []
            addr_str = items[0].get("title") if items else "Unknown"
        return (f"*{addr_str}", "Address")

    def lookup_place(self, coord: tuple[float, float], accuracy_m: float) -> tuple[str, str]:
        self.init_here_api()
        lat, lon = coord
        max_distance_m = math.ceil(self.lookup_tolerance_m + accuracy_m)
        if self.here_mode == "legacy":
            reply = self.discover_service.get(
                "/browse",
                {
                    "at": f"{lat},{lon}",
                    "in": f"circle:{lat},{lon};r={max_distance_m}",
                    "categories": "100,200,300,350,400,500,550,600,700,800,900",
                    "limit": 4,
                },
            )
            items = reply.get("items")
        else:
            reply = self.here_api.browse(
                center=[lat, lon],
                radius=max_distance_m,
                categories=["100", "200", "300", "350", "400", "500", "550", "600", "700", "800", "900"],
                limit=4,
            )
            items = getattr(reply, "items", [])
        if not items:
            return ("Unknown", "Unknown")

        names: list[str] = []
        categories: list[str] = []
        for item in items:
            if item.get("resultType") == "place":
                names.append(item.get("title"))
            item_categories = item.get("categories")
            if item_categories and item_categories[0].get("name"):
                categories.append(item_categories[0].get("name"))

        addr = items[0].get("address")
        if addr:
            addr_str = (
                f"{addr.get('houseNumber')} {addr.get('street')}, "
                f"{addr.get('city')} {addr.get('stateCode')}, {addr.get('postalCode')}"
            )
        else:
            addr_str = ""

        if names:
            label = f"{', '.join(names)}, {addr_str}"
            category = ",".join(categories)
        else:
            label = "Traffic"
            category = "Traffic"
        return (f"*{label}", f'"{category}"')

    def lookup_coords(self, addr_str: str) -> str:
        self.init_here_api()
        if self.here_mode == "legacy":
            reply = self.geocode_service.get("/geocode", {"q": addr_str})
            loc = reply.get("items")[0].get("position")
            return f"{loc.get('lat')},{loc.get('lng')}"
        reply = self.here_api.geocode(query=addr_str, limit=1)
        items = getattr(reply, "items", []) or []
        if not items:
            return "0,0"
        loc = items[0].get("position", {})
        return f"{loc.get('lat', 0)},{loc.get('lng', 0)}"

    def get_address_list_by_distance(self, coord: tuple[float, float]) -> dict[float, dict] | None:
        if not self.known_addresses:
            return None
        known_addresses_by_distance: dict[float, dict] = {}
        for addr in self.known_addresses:
            addr_coord = (addr.get("latitude"), addr.get("longitude"))
            distance_from_addr = distance.euclidean(addr_coord, coord)
            known_addresses_by_distance[distance_from_addr] = addr
        return known_addresses_by_distance

    def get_closest_address_info(self, coord: tuple[float, float], accuracy_m: float) -> tuple[str, str] | None:
        known_addresses_by_distance = self.get_address_list_by_distance(coord)
        if not known_addresses_by_distance:
            return None
        if accuracy_m == 0.0:
            accuracy_m = self.lookup_tolerance_m

        closest_addr = known_addresses_by_distance[min(known_addresses_by_distance)]
        closest_addr_coord = (closest_addr.get("latitude"), closest_addr.get("longitude"))
        distance_to_closest_addr_km = geopy_distance_km(closest_addr_coord, coord)
        closest_addr_radius_m = closest_addr.get("radius", self.lookup_tolerance_m)
        closest_addr_range_km = (closest_addr_radius_m + accuracy_m) / 1000
        if distance_to_closest_addr_km <= closest_addr_range_km:
            return (closest_addr.get("name", "Unknown"), closest_addr.get("icon", "Unknown"))
        return None

    def get_address(self, coord: tuple[float, float], accuracy_m: float, lookup_missing: bool = False) -> tuple[str, str]:
        closest_addr_info = self.get_closest_address_info(coord, accuracy_m)
        if closest_addr_info:
            return closest_addr_info
        if lookup_missing:
            return self.lookup_place(coord, accuracy_m)
        return ("Unknown", "Unknown")


class GpxTrip:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.path = []
        self.total_distance_traveled_km = 0

    def add_if_traveled(self, point):
        dist_from_last_km = self.get_distance_km_from_last(point)
        if dist_from_last_km:
            self.total_distance_traveled_km += dist_from_last_km
        self.path.append(point)
        return len(self.path)

    def get_distance_km_from_last(self, point):
        if not self.path:
            return None
        return self.calc_distance_km(self.path[-1], point)

    def get_time_s_since_last(self, point):
        if not self.path:
            return None
        return (point.time - self.path[-1].time).total_seconds()

    def get_ave_speed_kmps_from_last(self, point):
        km_from_last = self.get_distance_km_from_last(point)
        sec_since_last = self.get_time_s_since_last(point)
        if km_from_last and sec_since_last:
            return km_from_last / sec_since_last
        return None

    def get_ave_speed_kph_from_last(self, point):
        last_point = self.path[-1]
        last_speed_kph = self.get_speed(last_point)
        speed_kph = self.get_speed(point)
        return (last_speed_kph + speed_kph) / 2

    def get_travel_distance(self, units):
        dist_value = self.total_distance_traveled_km * UNITS.km
        if units == "imperial":
            dist_value = dist_value.to(UNITS.mile)
        if units == "metric_m":
            dist_value = dist_value.to(UNITS.m)
        return dist_value

    def get_ext_data(self, point, tag):
        for ext_data in point.extensions:
            if ext_data.tag == tag:
                return ext_data.text
        return ""

    def get_accuracy(self, point):
        ext_data = self.get_ext_data(point, "accuracy")
        return float(ext_data) if ext_data else 0.0

    def get_speed(self, point):
        ext_data = self.get_ext_data(point, "speed")
        return float(ext_data) if ext_data else 0.0

    @lru_cache(maxsize=10000)
    def get_coord(self, point):
        return (point.latitude, point.longitude)

    def calc_distance_km(self, point_a, point_b):
        return geopy_distance_km(self.get_coord(point_a), self.get_coord(point_b))

    def get_direct_distance(self, units):
        diameter = self.calc_distance_km(self.path[0], self.path[-1]) * UNITS.km if len(self.path) >= 2 else 0 * UNITS.km
        if units == "metric_m":
            diameter = diameter.to(UNITS.m)
        if units == "imperial":
            diameter = diameter.to(UNITS.mile)
        return diameter

    def get_duration(self):
        if len(self.path) < 2:
            return None
        return self.path[-1].time - self.path[0].time

    def get_speeds(self):
        return [point.speed if point.speed else 0 for point in self.path]

    def get_run_ave_speed(self, units="metric_km"):
        trip_distance = self.get_travel_distance(units)
        duration_dt = self.get_duration()
        if trip_distance and duration_dt:
            ave_speed = trip_distance / (duration_dt.total_seconds() * UNITS.s)
            if units == "imperial":
                return ave_speed.to(UNITS.mph)
            if units == "metric_km":
                return ave_speed.to(UNITS.kph)
            if units == "metric_m":
                return ave_speed.to(UNITS.mps)
        return None

    def get_ave_speed(self, units="metric_km"):
        num_points = len(self.path)
        if not num_points:
            return None
        speed_list = self.get_speeds()
        ave_speed = (sum(speed_list) / num_points) * UNITS.mps
        if units == "imperial":
            ave_speed = ave_speed.to(UNITS.mph)
        if units == "metric_km":
            ave_speed = ave_speed.to(UNITS.kph)
        return ave_speed

    def get_min_speed(self, units="metric_km"):
        num_points = len(self.path)
        if not num_points:
            return None
        speed_list = self.get_speeds()
        min_speed = max(speed_list) * UNITS.mps
        if units == "imperial":
            min_speed = min_speed.to(UNITS.mph)
        if units == "metric_km":
            min_speed = min_speed.to(UNITS.kph)
        return min_speed

    def get_max_speed(self, units="metric_km"):
        num_points = len(self.path)
        if not num_points:
            return None
        speed_list = self.get_speeds()
        max_speed = max(speed_list) * UNITS.mps
        if units == "imperial":
            max_speed = max_speed.to(UNITS.mph)
        if units == "metric_km":
            max_speed = max_speed.to(UNITS.kph)
        return max_speed


class GpxTools:
    def __init__(self, min_distance_km=0.8, min_ave_speed_kmh=1.0, lookup_tolerance_m=10, here_enabled=False):
        self.min_distance_km = min_distance_km
        self.min_ave_speed_kph = min_ave_speed_kmh
        self.addr_lookup = GpxLookup(lookup_tolerance_m, here_enabled=here_enabled)
        self.trips = []

    def load_known_addresses(self, file_path):
        self.addr_lookup.load_known_addresses(file_path)

    def load_known_places(self, places: Iterable[dict]) -> None:
        self.addr_lookup.load_known_places(places)

    def get_csv_header(self, units="metric_km"):
        header_pre = "Start Date,Start Address,Start Category,Start Coordinates,End Date,End Address,End Category,End Coordinates"
        header_post = "Number of points"
        if units == "metric_km":
            return (
                f"{header_pre},Direct Distance (km),Distance Traveled (km),Trip Duration (hh:mm:ss),"
                f"Minimum Speed (km/h),Average Speed (km/h),Maximum Speed (km/h),{header_post}"
            )
        if units == "metric_m":
            return (
                f"{header_pre},Direct Distance (m),Distance Traveled (m),Trip Duration (s),"
                f"Minimum Speed (m/s),Average Speed (m/s),Maximum Speed (m/s),{header_post}"
            )
        if units == "imperial":
            return (
                f"{header_pre},Direct Distance (mile),Distance Traveled (mile),Trip Duration (hh:mm:ss),"
                f"Minimum Speed (mph),Average Speed (mph),Maximum Speed (mph),{header_post}"
            )
        return ""

    def get_csv_str(
        self,
        trip,
        lookup_addr=False,
        units="metric_km",
        tz_name: str | None = "US/Mountain",
        datetime_format="%a %m/%d/%Y %r %Z",
    ):
        if len(trip.path) < 2:
            return ""
        start_point = trip.path[0]
        end_point = trip.path[-1]

        start_time = start_point.time
        end_time = end_point.time
        if tz_name:
            tz_obj = pytz.timezone(tz_name)
            start_time = start_time.replace(tzinfo=timezone.utc).astimezone(tz=tz_obj)
            end_time = end_time.replace(tzinfo=timezone.utc).astimezone(tz=tz_obj)

        start_coord = trip.get_coord(start_point)
        end_coord = trip.get_coord(end_point)
        start_accuracy = trip.get_accuracy(start_point)
        end_accuracy = trip.get_accuracy(end_point)
        start_addr, start_cat = self.addr_lookup.get_address(start_coord, start_accuracy, lookup_addr)
        end_addr, end_cat = self.addr_lookup.get_address(end_coord, end_accuracy, lookup_addr)

        direct_dist = trip.get_direct_distance(units)
        travel_distance = trip.get_travel_distance(units)
        duration = trip.get_duration()
        min_speed = trip.get_min_speed(units)
        ave_speed = trip.get_ave_speed(units)
        if ave_speed == 0:
            ave_speed = trip.get_run_ave_speed(units)
        max_speed = trip.get_max_speed(units)
        num_points = len(trip.path)

        start_time_str = datetime.strftime(start_time, datetime_format)
        end_time_str = datetime.strftime(end_time, datetime_format)
        start_coord_str = "%s, %s" % (start_coord)
        end_coord_str = "%s, %s" % (end_coord)

        return (
            f'{start_time_str},"{start_addr}",{start_cat},"{start_coord_str}",'
            f'{end_time_str},"{end_addr}",{end_cat},"{end_coord_str}",'
            f"{direct_dist.magnitude},{travel_distance.magnitude},{duration},"
            f"{min_speed.magnitude},{ave_speed.magnitude},{max_speed.magnitude},{num_points}"
        )

    def load_trips(self, gpx_paths):
        min_ave_speed_kmps = (self.min_ave_speed_kph * UNITS.kph).to(UNITS.kmps).magnitude
        trip = GpxTrip()
        for gpx_file_path in gpx_paths:
            if os.stat(gpx_file_path).st_size == 0:
                continue
            with open(gpx_file_path, "r", encoding="utf-8") as gpx_file:
                gpx = gpxpy.parse(gpx_file)
            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        if trip.path:
                            ave_speed_kmps = trip.get_ave_speed_kmps_from_last(point)
                            if ave_speed_kmps and ave_speed_kmps <= min_ave_speed_kmps:
                                self._record_trip_and_reset(trip)
                        trip.add_if_traveled(point)
        self._record_trip_and_reset(trip)

    def _record_trip_and_reset(self, trip):
        if trip.get_direct_distance("metric_km").magnitude > self.min_distance_km:
            self.trips.append(copy(trip))
        trip.reset()

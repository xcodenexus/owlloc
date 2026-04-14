import xml.etree.ElementTree as ET
from typing import List, Dict


# GPX namespaces
_NAMESPACES = [
    "http://www.topografix.com/GPX/1/1",
    "http://www.topografix.com/GPX/1/0",
    "",
]


def _find_points(root: ET.Element) -> List[Dict[str, float]]:
    points = []

    def try_ns(tag: str, ns: str) -> str:
        if ns:
            return f"{{{ns}}}{tag}"
        return tag

    for ns in _NAMESPACES:
        # Track points
        for trkpt in root.iter(try_ns("trkpt", ns)):
            try:
                lat = float(trkpt.get("lat"))
                lon = float(trkpt.get("lon"))
                points.append({"lat": lat, "lng": lon})
            except (TypeError, ValueError):
                continue

        if points:
            return points

        # Route points
        for rtept in root.iter(try_ns("rtept", ns)):
            try:
                lat = float(rtept.get("lat"))
                lon = float(rtept.get("lon"))
                points.append({"lat": lat, "lng": lon})
            except (TypeError, ValueError):
                continue

        if points:
            return points

        # Waypoints
        for wpt in root.iter(try_ns("wpt", ns)):
            try:
                lat = float(wpt.get("lat"))
                lon = float(wpt.get("lon"))
                points.append({"lat": lat, "lng": lon})
            except (TypeError, ValueError):
                continue

        if points:
            return points

    return points


def parse(file_path: str) -> List[Dict[str, float]]:
    """Parse a GPX file and return a list of {lat, lng} dicts."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        points = _find_points(root)
        if not points:
            raise ValueError("No trackpoints found in GPX file")
        return points
    except ET.ParseError as e:
        raise ValueError(f"Invalid GPX file: {e}")

#!/usr/bin/env python3
"""Build the reviewed Canada raised-crosswalk point snapshot.

The national fallback is deliberately strict: an OpenStreetMap feature must be
both a speed table and a pedestrian crossing.  Generic speed tables and speed
humps are not raised crosswalks and are excluded.  Where an openly licensed
municipal inventory explicitly identifies a raised crosswalk, that record wins
over nearby OSM geometry.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


HALIFAX_LAYER = (
    "https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/"
    "Traffic_Calming_Infrastructure/FeatureServer/0"
)
HALIFAX_DATASET = "https://data-hrm.hub.arcgis.com/datasets/traffic-calming-infrastructure"
OSM_SOURCE = "https://download.geofabrik.de/north-america/canada.html"
OSM_LICENSE = "https://www.openstreetmap.org/copyright"
DEDUPLICATION_METRES = 20.0


def _get_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    request_url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        request_url,
        headers={"User-Agent": "aportee-datasets/1.0 (https://aportee.ca)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object from {url}")
    return value


def _halifax_features() -> list[dict[str, Any]]:
    collection = _get_json(
        f"{HALIFAX_LAYER}/query",
        {
            "where": "ASSETCODE='RSDCRW' AND ASSETSTAT='INS'",
            "outFields": (
                "TRCMID,ASSETID,ASSETCODE,OWNER,LOCGEN,INSTYR,ASSETDESC,"
                "ASSETSTAT,LOCATION,SDATE"
            ),
            "outSR": "4326",
            "returnGeometry": "true",
            "f": "geojson",
        },
    )
    output: list[dict[str, Any]] = []
    for feature in collection.get("features", []):
        properties = feature.get("properties") or {}
        source_id = str(properties.get("ASSETID") or properties.get("TRCMID") or "").strip()
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates")
        if not source_id or geometry.get("type") != "Point" or not _valid_point(coordinates):
            continue
        location = str(properties.get("LOCATION") or "").strip()
        output.append(
            {
                "type": "Feature",
                "id": f"halifax:{source_id}",
                "geometry": {"type": "Point", "coordinates": coordinates[:2]},
                "properties": {
                    "name": f"Raised crosswalk — {location}" if location else "Raised crosswalk",
                    "feature_type": "raised_crosswalk",
                    "source": "Halifax Regional Municipality",
                    "source_id": source_id,
                    "source_url": HALIFAX_DATASET,
                    "evidence": "authoritative_inventory",
                    "licence": "Open Government Licence — Halifax",
                    "municipality": "Halifax Regional Municipality",
                    "install_year": properties.get("INSTYR"),
                },
            }
        )
    return output


def _valid_point(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(item, (int, float)) and math.isfinite(item) for item in value[:2])
        and -180 <= value[0] <= 180
        and -90 <= value[1] <= 90
    )


def _iter_geojson_sequence(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.lstrip("\x1e").strip()
            if line:
                value = json.loads(line)
                if isinstance(value, dict):
                    yield value


def _line_coordinates(geometry: dict[str, Any]) -> list[list[float]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "LineString" and isinstance(coordinates, list):
        return [point for point in coordinates if _valid_point(point)]
    if geometry_type == "MultiLineString" and isinstance(coordinates, list):
        return [
            point
            for line in coordinates
            if isinstance(line, list)
            for point in line
            if _valid_point(point)
        ]
    return []


def _midpoint(points: list[list[float]]) -> list[float]:
    if not points:
        raise ValueError("cannot calculate a midpoint without coordinates")
    if len(points) == 1:
        return points[0][:2]
    lengths = [_haversine(a, b) for a, b in zip(points, points[1:], strict=False)]
    target = sum(lengths) / 2
    elapsed = 0.0
    for start, end, length in zip(points, points[1:], lengths, strict=True):
        if elapsed + length >= target:
            fraction = 0 if length == 0 else (target - elapsed) / length
            return [
                start[0] + fraction * (end[0] - start[0]),
                start[1] + fraction * (end[1] - start[1]),
            ]
        elapsed += length
    return points[-1][:2]


def _haversine(left: list[float], right: list[float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, [left[0], left[1], right[0], right[1]])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_008.8 * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _osm_timestamp(pbf: Path) -> str | None:
    result = subprocess.run(
        ["osmium", "fileinfo", "-g", "header.option.osmosis_replication_timestamp", str(pbf)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


def _osm_features(
    pbf_paths: list[Path],
) -> tuple[list[dict[str, Any]], dict[str, str | None], dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, str | None] = {}
    with tempfile.TemporaryDirectory(prefix="raised-crosswalks-") as directory:
        root = Path(directory)
        for pbf in pbf_paths:
            snapshots[pbf.name] = _osm_timestamp(pbf)
            filtered = root / f"{pbf.stem}-tables.osm.pbf"
            exported = root / f"{pbf.stem}-tables.geojsonseq"
            subprocess.run(
                [
                    "osmium",
                    "tags-filter",
                    str(pbf),
                    "nwr/traffic_calming=table",
                    "-o",
                    str(filtered),
                    "--overwrite",
                ],
                check=True,
            )
            subprocess.run(
                [
                    "osmium",
                    "export",
                    str(filtered),
                    "-f",
                    "geojsonseq",
                    "-u",
                    "type_id",
                    "-a",
                    "version,timestamp",
                    "-o",
                    str(exported),
                    "--overwrite",
                ],
                check=True,
            )
            for feature in _iter_geojson_sequence(exported):
                properties = feature.get("properties") or {}
                if properties.get("traffic_calming") != "table" or not (
                    properties.get("highway") == "crossing"
                    or properties.get("footway") == "crossing"
                ):
                    continue
                source_id = feature.get("id")
                geometry = feature.get("geometry") or {}
                if not isinstance(source_id, str) or not source_id:
                    continue
                if geometry.get("type") == "Point" and _valid_point(geometry.get("coordinates")):
                    point = geometry["coordinates"][:2]
                    vertices = [point]
                else:
                    vertices = _line_coordinates(geometry)
                    if not vertices:
                        continue
                    point = _midpoint(vertices)
                candidates[source_id] = {
                    "point": point,
                    "vertices": vertices,
                    "properties": properties,
                    "extract": pbf.name,
                }

    # A crossing way often carries the same tags as one of its member nodes.
    # Prefer the node and drop only ways that contain an exact strict node; a
    # proximity-only merge would collapse distinct crossings at small junctions.
    node_coordinates = {
        (round(value["point"][0], 7), round(value["point"][1], 7))
        for source_id, value in candidates.items()
        if source_id.startswith("n")
    }
    output: list[dict[str, Any]] = []
    way_duplicates_removed = 0
    for source_id, value in sorted(candidates.items()):
        if source_id.startswith("w") and any(
            (round(point[0], 7), round(point[1], 7)) in node_coordinates
            for point in value["vertices"]
        ):
            way_duplicates_removed += 1
            continue
        properties = value["properties"]
        name = str(properties.get("name") or "").strip()
        output.append(
            {
                "type": "Feature",
                "id": f"osm:{source_id}",
                "geometry": {"type": "Point", "coordinates": value["point"]},
                "properties": {
                    "name": name or "Raised crosswalk",
                    "feature_type": "raised_crosswalk",
                    "source": "OpenStreetMap",
                    "source_id": source_id,
                    "source_url": f"https://www.openstreetmap.org/{'node' if source_id[0] == 'n' else 'way'}/{source_id[1:]}",
                    "source_extract": value["extract"],
                    "evidence": "community_mapped_table_and_crossing",
                    "licence": "Open Data Commons Open Database License 1.0",
                    "osm_version": properties.get("@version"),
                    "osm_timestamp": properties.get("@timestamp"),
                },
            }
        )
    by_extract = Counter(
        feature["properties"]["source_extract"] for feature in output
    )
    return (
        output,
        snapshots,
        {
            "strict_candidates": len(candidates),
            "way_duplicates_removed": way_duplicates_removed,
            "by_extract": dict(sorted(by_extract.items())),
        },
    )


def _deduplicate(
    authoritative: list[dict[str, Any]], fallback: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    authoritative_points = [feature["geometry"]["coordinates"] for feature in authoritative]
    kept = list(authoritative)
    removed = 0
    for feature in fallback:
        point = feature["geometry"]["coordinates"]
        if any(_haversine(point, other) <= DEDUPLICATION_METRES for other in authoritative_points):
            removed += 1
        else:
            kept.append(feature)
    return kept, removed


def build(pbf_dir: Path) -> dict[str, Any]:
    pbf_paths = sorted(pbf_dir.glob("*-latest.osm.pbf"))
    if not pbf_paths:
        raise ValueError(f"no *-latest.osm.pbf files found in {pbf_dir}")
    authoritative = _halifax_features()
    osm, snapshots, osm_counts = _osm_features(pbf_paths)
    features, removed = _deduplicate(authoritative, osm)
    features.sort(key=lambda feature: feature["id"])
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "type": "FeatureCollection",
        "metadata": {
            "label": "Canada raised crosswalks",
            "description": (
                "A non-exhaustive inventory of explicitly identified raised crosswalks. "
                "It combines openly licensed municipal inventory records with strict "
                "OpenStreetMap table-plus-crossing features."
            ),
            "generated_at": now,
            "coverage": "Canada (non-exhaustive; mapping completeness varies by municipality)",
            "feature_type": "raised_crosswalk",
            "excluded": ["generic speed tables", "speed humps", "raised intersections"],
            "deduplication_metres": DEDUPLICATION_METRES,
            "counts": {
                "authoritative_inventory": len(authoritative),
                "osm_strict_candidates": osm_counts["strict_candidates"],
                "osm_way_duplicates_removed": osm_counts["way_duplicates_removed"],
                "osm_strict_before_authoritative_deduplication": len(osm),
                "osm_removed_near_authoritative": removed,
                "osm_by_extract": osm_counts["by_extract"],
                "total": len(features),
            },
            "sources": [
                {
                    "name": "Halifax Traffic Calming Infrastructure",
                    "url": HALIFAX_DATASET,
                    "filter": "ASSETCODE=RSDCRW and ASSETSTAT=INS",
                    "licence": "Open Government Licence — Halifax",
                },
                {
                    "name": "OpenStreetMap Canada extracts",
                    "url": OSM_SOURCE,
                    "filter": (
                        "traffic_calming=table and "
                        "(highway=crossing or footway=crossing)"
                    ),
                    "licence": OSM_LICENSE,
                    "extract_snapshots": snapshots,
                },
            ],
        },
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pbf-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset = build(args.pbf_dir)
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {len(dataset['features'])} raised crosswalks to {args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()

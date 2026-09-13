#!/usr/bin/env python3
"""Build municipal-recorded raised crosswalks; never infer them from OSM tags.

The source allowlist requires an explicit raised-crosswalk classification,
an in-service status, a traceable municipal record ID and reviewed reuse terms.
Municipal classification is evidence, not independent field verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SOURCES = (
    {
        "key": "halifax",
        "municipality": "Halifax Regional Municipality",
        "province": "NS",
        "layer": "https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/Traffic_Calming_Infrastructure/FeatureServer/0",
        "url": "https://data-hrm.hub.arcgis.com/datasets/traffic-calming-infrastructure",
        "criteria": {"ASSETCODE": "RSDCRW", "ASSETSTAT": "INS"},
        "id_field": "ASSETID",
        "location_fields": ["LOCATION"],
        "year_field": "INSTYR",
        "licence": "Open Government Licence — Halifax",
        "licence_url": "https://www.halifax.ca/home/open-data/open-data-licence",
        "attribution": "Contains information licensed under the Open Government Licence – Halifax.",
    },
    {
        "key": "surrey",
        "municipality": "City of Surrey",
        "province": "BC",
        "layer": "https://gisservices.surrey.ca/arcgis/rest/services/OpenData/MapServer/116",
        "url": "https://www.arcgis.com/home/item.html?id=9dd77c3dbf544a1989ca0f95371b6da1",
        "criteria": {"DEVICE_TYPE2": "Raised Crossing", "STATUS": "In Service"},
        "id_field": "FACILITYID",
        "fallback_id_field": "OBJECTID",
        "location_fields": ["LOCATION"],
        "year_field": "YEAR_BUILT",
        "licence": "Open Government License — City of Surrey",
        "licence_url": "https://opendata-surrey.hub.arcgis.com/pages/55089a19491a4fe59a41e059fd8af708",
        "attribution": "Contains information licensed under the Open Government License – City of Surrey.",
    },
    {
        "key": "kitchener",
        "municipality": "City of Kitchener",
        "province": "ON",
        "layer": "https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Calming/FeatureServer/0",
        "url": "https://www.arcgis.com/home/item.html?id=2751362c6d5046d997fe166aa6f6e11a",
        "criteria": {"CATEGORY": "RAISED CROSSWALK", "STATUS": "ACTIVE"},
        "id_field": "TRAFFICCALMINGID",
        "location_fields": ["STREET", "LOCATION_DESCRIPTION"],
        "year_field": "INSTALL_YEAR",
        "licence": "Open Government Licence — The Corporation of the City of Kitchener",
        "licence_url": "https://www.arcgis.com/home/item.html?id=2751362c6d5046d997fe166aa6f6e11a",
        "attribution": "Contains information licensed under the Open Government Licence - The Corporation of the City of Kitchener.",
    },
)


def _get_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "aportee-datasets/2.0 (https://aportee.ca)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        value = json.load(response)
    if not isinstance(value, dict) or "error" in value:
        raise ValueError(f"invalid ArcGIS response from {url}: {value}")
    return value


def _where(source: dict[str, Any]) -> str:
    return " AND ".join(f"{key}='{value}'" for key, value in source["criteria"].items())


def _fetch_records(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch by enumerated IDs, avoiding silent ArcGIS transfer-limit truncation."""
    url = f"{source['layer']}/query"
    index = _get_json(
        url, {"f": "json", "where": _where(source), "returnIdsOnly": "true"}
    )
    ids = index.get("objectIds")
    id_field = index.get("objectIdFieldName")
    if not isinstance(ids, list) or not ids or not isinstance(id_field, str):
        raise ValueError(
            f"{source['key']}: missing/empty object ID list; review source before publishing"
        )
    if any(type(value) is not int for value in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"{source['key']}: invalid or duplicate object IDs")
    fields = list(
        dict.fromkeys(
            [
                id_field,
                source["id_field"],
                *source["criteria"],
                *source["location_fields"],
                source["year_field"],
            ]
        )
    )
    records = []
    for offset in range(0, len(ids), 200):
        batch = ids[offset : offset + 200]
        page = _get_json(
            url,
            {
                "f": "json",
                "where": _where(source),
                "objectIds": ",".join(map(str, batch)),
                "outFields": ",".join(fields),
                "returnGeometry": "true",
                "outSR": "4326",
            },
        )
        reference = page.get("spatialReference") or {}
        if reference.get("latestWkid", reference.get("wkid")) != 4326:
            raise ValueError(f"{source['key']}: response is not EPSG:4326")
        features = page.get("features")
        if not isinstance(features, list) or page.get("exceededTransferLimit"):
            raise ValueError(f"{source['key']}: incomplete feature response")
        returned = [
            (feature.get("attributes") or {}).get(id_field) for feature in features
        ]
        if len(returned) != len(batch) or set(returned) != set(batch):
            raise ValueError(
                f"{source['key']}: missing/duplicate/changed source records; retry and review"
            )
        records.extend(features)
    return records


def _valid_point(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 2
        and all(
            type(item) in (int, float) and math.isfinite(item) for item in value[:2]
        )
        and -180 <= value[0] <= 180
        and -90 <= value[1] <= 90
    )


def _distance(left: list[float], right: list[float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, [*left[:2], *right[:2]])
    value = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6_371_008.8 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, value))))


def _geometry(raw: dict[str, Any]) -> tuple[list[float], dict[str, Any]]:
    if "x" in raw and "y" in raw:
        point = [raw["x"], raw["y"]]
        if _valid_point(point):
            return point, {"type": "Point", "coordinates": point}
    paths = raw.get("paths")
    if (
        not isinstance(paths, list)
        or not paths
        or any(
            not isinstance(path, list)
            or len(path) < 2
            or not all(_valid_point(p) for p in path)
            for path in paths
        )
    ):
        raise ValueError("expected a valid point or polyline")
    paths = [[point[:2] for point in path] for path in paths]
    # Walk only real segments, never an invented link between multipart lines.
    segments = [
        (a, b, _distance(a, b))
        for path in paths
        for a, b in zip(path, path[1:], strict=False)
    ]
    length = sum(segment[2] for segment in segments)
    if length <= 0:
        raise ValueError("zero-length source polyline")
    remaining = length / 2
    point = paths[-1][-1]
    for start, end, segment_length in segments:
        if segment_length > 0 and remaining <= segment_length:
            fraction = remaining / segment_length
            point = [start[i] + fraction * (end[i] - start[i]) for i in range(2)]
            break
        remaining -= segment_length
    native = (
        {"type": "LineString", "coordinates": paths[0]}
        if len(paths) == 1
        else {
            "type": "MultiLineString",
            "coordinates": paths,
        }
    )
    return point, native


def _normalize(
    source: dict[str, Any], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    seen = {}
    for record in records:
        attributes = record.get("attributes") or {}
        # Recheck returned attributes: do not trust a URL filter as validation.
        if any(
            attributes.get(key) != value for key, value in source["criteria"].items()
        ):
            raise ValueError(
                f"{source['key']}: record is not an explicitly raised, in-service crosswalk"
            )
        raw_id = attributes.get(source["id_field"])
        id_basis = "municipal_asset_id"
        if raw_id is None or not str(raw_id).strip():
            fallback = source.get("fallback_id_field")
            raw_id = attributes.get(fallback) if fallback else None
            id_basis = "service_object_id_snapshot_scoped"
        if raw_id is None or isinstance(raw_id, bool) or not str(raw_id).strip():
            raise ValueError(f"{source['key']}: missing municipal record ID")
        source_id = str(raw_id).strip()
        if id_basis == "service_object_id_snapshot_scoped":
            source_id = f"objectid:{source_id}"
        point, native = _geometry(record.get("geometry") or {})
        if source_id in seen:
            previous = seen[source_id]
            previous_attributes = previous["properties"]["source_attributes"]

            def comparable(attrs):
                return {key: value for key, value in attrs.items() if key != "OBJECTID"}

            # Same asset ID, identical attributes and <=1 cm point displacement:
            # duplicated municipal record, not a proximity-only crossing match.
            if (
                id_basis == "municipal_asset_id"
                and native["type"]
                == previous["properties"]["source_geometry"]["type"]
                == "Point"
                and comparable(attributes) == comparable(previous_attributes)
                and _distance(point, previous["geometry"]["coordinates"]) <= 0.01
            ):
                previous["properties"]["duplicate_source_records"].append(record)
                continue
            raise ValueError(
                f"{source['key']}: conflicting duplicate municipal asset ID {source_id}"
            )
        location = " — ".join(
            str(attributes.get(field) or "").strip()
            for field in source["location_fields"]
            if attributes.get(field)
        )
        feature = {
            "type": "Feature",
            "id": f"{source['key']}:{source_id}",
            "geometry": {"type": "Point", "coordinates": point},
            "properties": {
                "name": f"Raised crosswalk — {location}"
                if location
                else "Raised crosswalk",
                "feature_type": "raised_crosswalk",
                "source": source["municipality"],
                "source_id": source_id,
                "source_url": source["url"],
                "source_id_basis": id_basis,
                "duplicate_source_records": [],
                "source_layer_url": source["layer"],
                "source_attributes": attributes,
                "source_geometry": native,
                "source_geometry_crs": "EPSG:4326",
                "evidence": "authoritative_inventory",
                "verification": "municipal_record_not_field_verified",
                "status": "in_service",
                "licence": source["licence"],
                "licence_url": source["licence_url"],
                "attribution": source["attribution"],
                "municipality": source["municipality"],
                "province": source["province"],
                "install_year": attributes.get(source["year_field"]),
            },
        }
        output.append(feature)
        seen[source_id] = feature
    return output


def build() -> dict[str, Any]:
    features = []
    receipts = []
    for source in SOURCES:
        records = _fetch_records(source)
        records.sort(
            key=lambda record: (
                str(record["attributes"].get(source["id_field"])),
                str(record["attributes"].get("OBJECTID")),
            )
        )
        normalized = _normalize(source, records)
        features.extend(normalized)
        receipts.append(
            {
                "name": source["municipality"],
                "url": source["url"],
                "layer_url": source["layer"],
                "filter": _where(source),
                "licence": source["licence"],
                "licence_url": source["licence_url"],
                "attribution": source["attribution"],
                "retrieved_at": datetime.now(UTC).isoformat(),
                "count": len(normalized),
                "raw_record_count": len(records),
                "duplicate_records_collapsed": len(records) - len(normalized),
                "records_sha256": hashlib.sha256(
                    json.dumps(records, sort_keys=True, allow_nan=False).encode()
                ).hexdigest(),
            }
        )
    features.sort(key=lambda feature: feature["id"])
    return {
        "type": "FeatureCollection",
        "metadata": {
            "label": "Canada raised crosswalks",
            "description": "Non-exhaustive municipal inventory records explicitly identifying in-service raised crosswalks. No OSM-derived or inferred crossings; not independently field verified.",
            "generated_at": datetime.now(UTC).isoformat(),
            "coverage": "Canada scope; current municipal coverage: Halifax, Surrey and Kitchener only. Absence is not evidence that a municipality has no raised crosswalks.",
            "feature_type": "raised_crosswalk",
            "inclusion_policy": "municipal_explicit_raised_crosswalk_in_service_v1",
            "excluded": [
                "OSM-derived records",
                "generic speed tables",
                "speed humps",
                "raised intersections",
                "textured crosswalks without an explicit raised classification",
                "proposed, removed or unknown-status assets",
                "sources without reviewed reuse terms",
            ],
            "counts": {
                "authoritative_inventory": len(features),
                "total": len(features),
                "municipal_source_records": sum(
                    r["raw_record_count"] for r in receipts
                ),
                "duplicate_records_collapsed": sum(
                    r["duplicate_records_collapsed"] for r in receipts
                ),
                "by_municipality": dict(
                    sorted(
                        Counter(
                            f["properties"]["municipality"] for f in features
                        ).items()
                    )
                ),
            },
            "sources": receipts,
        },
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    dataset = build()  # Validate every source before touching the output snapshot.
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {len(dataset['features'])} municipal-recorded raised crosswalks to {args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()

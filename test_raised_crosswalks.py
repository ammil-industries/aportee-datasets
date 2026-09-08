"""Offline policy, adapter and snapshot regressions (stdlib unittest)."""

import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "raised", ROOT / "build-canada-raised-crosswalks.py"
)
raised = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(raised)


def record(source, asset_id="asset-1", object_id=1):
    return {
        "attributes": {
            "OBJECTID": object_id,
            source["id_field"]: asset_id,
            **source["criteria"],
        },
        "geometry": {"x": -123.0, "y": 49.0},
    }


class MunicipalPolicyTests(unittest.TestCase):
    def test_all_sources_have_exact_positive_class_and_status_checks(self):
        self.assertEqual(
            {s["key"] for s in raised.SOURCES}, {"halifax", "surrey", "kitchener"}
        )
        for source in raised.SOURCES:
            with self.subTest(source=source["key"]):
                feature = raised._normalize(source, [record(source)])[0]
                self.assertEqual(
                    feature["properties"]["evidence"], "authoritative_inventory"
                )
                self.assertEqual(
                    feature["properties"]["verification"],
                    "municipal_record_not_field_verified",
                )
                self.assertTrue(source["licence_url"].startswith("https://"))
                for field in source["criteria"]:
                    for value in (
                        None,
                        "",
                        "Speed Table",
                        "Proposed",
                        "REMOVED",
                        "UNKNOWN",
                    ):
                        invalid = record(source)
                        invalid["attributes"][field] = value
                        with self.assertRaisesRegex(
                            ValueError, "not an explicitly raised"
                        ):
                            raised._normalize(source, [invalid])

    def test_osm_tags_are_not_evidence_for_any_adapter(self):
        for source in raised.SOURCES:
            candidate = record(source)
            candidate["attributes"] = {
                "traffic_calming": "table",
                "highway": "crossing",
            }
            with self.assertRaises(ValueError):
                raised._normalize(source, [candidate])

    def test_missing_asset_id_fails_without_reviewed_fallback(self):
        for source in (raised.SOURCES[0], raised.SOURCES[2]):
            with self.assertRaisesRegex(ValueError, "missing municipal record ID"):
                raised._normalize(source, [record(source, None)])

    def test_surrey_fallback_ids_are_explicitly_snapshot_scoped(self):
        source = raised.SOURCES[1]
        feature = raised._normalize(source, [record(source, None, 155954)])[0]
        self.assertEqual(feature["id"], "surrey:objectid:155954")
        self.assertEqual(
            feature["properties"]["source_id_basis"],
            "service_object_id_snapshot_scoped",
        )

    def test_duplicate_asset_requires_same_attributes_and_nearly_exact_geometry(self):
        source = raised.SOURCES[1]
        first, second = record(source), record(source, object_id=2)
        second["geometry"]["x"] += 1e-9
        features = raised._normalize(source, [first, second])
        self.assertEqual(len(features), 1)
        self.assertEqual(
            features[0]["properties"]["duplicate_source_records"], [second]
        )
        second["geometry"]["x"] += 0.00001  # <20 m is NOT sufficient evidence.
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            raised._normalize(source, [first, second])
        second = record(source, object_id=2)
        second["attributes"]["LOCATION"] = "different crossing"
        with self.assertRaisesRegex(ValueError, "conflicting duplicate"):
            raised._normalize(source, [first, second])

    def test_close_distinct_assets_are_not_merged(self):
        source = raised.SOURCES[1]
        self.assertEqual(
            len(
                raised._normalize(source, [record(source, "a"), record(source, "b", 2)])
            ),
            2,
        )

    def test_polyline_is_preserved_and_midpoint_is_length_weighted(self):
        point, native = raised._geometry({"paths": [[[0, 0], [1, 0], [4, 0]]]})
        self.assertAlmostEqual(point[0], 2)
        self.assertEqual(
            native, {"type": "LineString", "coordinates": [[0, 0], [1, 0], [4, 0]]}
        )

    def test_multipart_midpoint_does_not_connect_disjoint_lines(self):
        point, native = raised._geometry(
            {"paths": [[[0, 0], [1, 0]], [[10, 0], [13, 0]]]}
        )
        self.assertAlmostEqual(point[0], 11)
        self.assertEqual(native["type"], "MultiLineString")

    def test_bad_geometry_is_not_silently_skipped(self):
        for raw in (
            {},
            {"x": True, "y": 49},
            {"x": float("nan"), "y": 49},
            {"paths": [[[0, 0], [0, 0]]]},
            {"paths": [[[0, 0], [200, 0]]]},
        ):
            with self.assertRaises(ValueError):
                raised._geometry(raw)


class ArcGISTests(unittest.TestCase):
    def test_batches_cover_every_enumerated_object_id(self):
        source = raised.SOURCES[0]
        ids = list(range(205))

        def fetch(url, params):
            self.assertEqual(params["where"], raised._where(source))
            if params.get("returnIdsOnly"):
                return {"objectIds": ids, "objectIdFieldName": "OBJECTID"}
            selected = list(map(int, params["objectIds"].split(",")))
            self.assertLessEqual(len(selected), 200)
            return {
                "spatialReference": {"wkid": 4326},
                "features": [record(source, str(i), i) for i in selected],
            }

        with patch.object(raised, "_get_json", side_effect=fetch) as get:
            records = raised._fetch_records(source)
        self.assertEqual(len(records), 205)
        self.assertEqual(get.call_count, 3)

    def test_truncated_missing_duplicate_or_wrong_crs_pages_fail(self):
        source = raised.SOURCES[0]
        index = {"objectIds": [1, 2], "objectIdFieldName": "OBJECTID"}
        valid = {
            "spatialReference": {"wkid": 4326},
            "features": [record(source, "a", 1), record(source, "b", 2)],
        }
        pages = [
            dict(valid, exceededTransferLimit=True),
            dict(valid, features=[]),
            dict(valid, features=[record(source), record(source)]),
            dict(valid, spatialReference={"wkid": 26910}),
        ]
        for page in pages:
            with (
                patch.object(raised, "_get_json", side_effect=[index, page]),
                self.assertRaises(ValueError),
            ):
                raised._fetch_records(source)

    def test_empty_or_broken_source_does_not_silently_publish(self):
        for index in (
            {},
            {"objectIds": [], "objectIdFieldName": "OBJECTID"},
            {"objectIds": [1, 1], "objectIdFieldName": "OBJECTID"},
        ):
            with (
                patch.object(raised, "_get_json", return_value=index),
                self.assertRaises(ValueError),
            ):
                raised._fetch_records(raised.SOURCES[0])

    def test_http_200_arcgis_errors_raise(self):
        response = io.BytesIO(b'{"error":{"code":400,"message":"Bad query"}}')
        with (
            patch.object(raised.urllib.request, "urlopen", return_value=response),
            self.assertRaises(ValueError),
        ):
            raised._get_json("https://example.com/query", {})


class SnapshotTests(unittest.TestCase):
    def test_builder_has_no_fallback_and_reports_raw_and_unique_counts(self):
        def fetch(source):
            return [record(source)]

        with patch.object(raised, "_fetch_records", side_effect=fetch):
            result = raised.build()
        self.assertEqual(result["metadata"]["counts"]["total"], 3)
        self.assertEqual(result["metadata"]["counts"]["municipal_source_records"], 3)
        self.assertNotIn("osm_strict_candidates", result["metadata"]["counts"])

    def test_committed_snapshot_contains_only_allowlisted_municipal_evidence(self):
        dataset = json.loads((ROOT / "canada-raised-crosswalks.geojson").read_text())
        features = dataset["features"]
        self.assertTrue(features)
        self.assertEqual(len({f["id"] for f in features}), len(features))
        self.assertEqual(dataset["metadata"]["counts"]["total"], len(features))
        by_key = {source["key"]: source for source in raised.SOURCES}
        for feature in features:
            key = feature["id"].split(":", 1)[0]
            self.assertIn(key, by_key)
            source, props = by_key[key], feature["properties"]
            self.assertEqual(props["evidence"], "authoritative_inventory")
            self.assertEqual(props["status"], "in_service")
            self.assertEqual(props["source"], source["municipality"])
            self.assertTrue(raised._valid_point(feature["geometry"]["coordinates"]))
            for field, value in source["criteria"].items():
                self.assertEqual(props["source_attributes"][field], value)


if __name__ == "__main__":
    unittest.main()

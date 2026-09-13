# à portée public datasets

This repository contains source datasets used to build custom layers for
[à portée](https://aportee.ca). Files on `main` are intentionally mutable:
publishing a new snapshot does not update the map until the routed artifacts are
rebuilt and published separately.

## Victoria Lime parking zones

`victoria-lime-zones.geojson` is a 129-point snapshot of the City of Victoria's
Lime e-bike parking zones. The source snapshot was imported from this public
Google My Maps KML export:

```text
https://www.google.com/maps/d/kml?mid=1S7Y4HQ6dr7khxBLoDMfmzNYulUuDNQY&forcekml=1
```

The GeoJSON retains that source URL and its retrieval timestamp in the
metadata.

The file is consumed through this stable raw URL:

```text
https://raw.githubusercontent.com/ammil-industries/aportee-datasets/main/victoria-lime-zones.geojson
```

`victoria-lime-logo.svg` is the official neon-green horizontal Lime logo from
[Lime's public press portal](https://www.li.me/about/press). Lime owns the Lime
name, logo, and associated trademarks; the asset is included only to identify
the corresponding dataset in the à portée interface.

The logo is consumed through this stable raw URL:

```text
https://raw.githubusercontent.com/ammil-industries/aportee-datasets/main/victoria-lime-logo.svg
```

After updating the file, rerun the reviewed custom-access definition and publish
the resulting development tileset. Updating this repository alone does not
change the website.

## Canada raised crosswalks

`canada-raised-crosswalks.geojson` is a deliberately non-exhaustive national
inventory of **municipal-recorded, in-service raised crosswalks only**. Inclusion
requires an explicit municipal raised-crosswalk classification, a current
in-service status and reviewed reuse terms. There is no OSM fallback, including
for features tagged as both a speed table and a crossing. Generic speed tables,
speed humps, raised intersections, and textured crossings without an explicit
raised classification are excluded. Missing coverage does not mean no raised
crosswalks exist in that municipality.

The 8 September 2026 snapshot contains **114 features** from 115 municipal
records: Halifax 10, Surrey 67 (68 records, one confirmed duplicate), Kitchener
37. It replaces the previous snapshot's 1,487 OSM-derived records. A user's
Victoria spot check found only one of four sampled OSM-derived candidates was
raised; that is not a national error-rate estimate, but it is sufficient reason
to withdraw the unverified fallback. These municipal records are **not claimed
to be independently field verified** either.

| Source | Required classification and status | Reuse terms |
|---|---|---|
| [Halifax Traffic Calming Infrastructure](https://data-hrm.hub.arcgis.com/datasets/traffic-calming-infrastructure) | `ASSETCODE=RSDCRW`, `ASSETSTAT=INS` | [Open Government Licence — Halifax](https://www.halifax.ca/home/open-data/open-data-licence) |
| [Surrey Traffic Calming](https://www.arcgis.com/home/item.html?id=9dd77c3dbf544a1989ca0f95371b6da1) | `DEVICE_TYPE2=Raised Crossing`, `STATUS=In Service` | [Open Government License — City of Surrey](https://opendata-surrey.hub.arcgis.com/pages/55089a19491a4fe59a41e059fd8af708) |
| [Kitchener Traffic Calming](https://www.arcgis.com/home/item.html?id=2751362c6d5046d997fe166aa6f6e11a) | `CATEGORY=RAISED CROSSWALK`, `STATUS=ACTIVE` | Open Government Licence — The Corporation of the City of Kitchener, published in the linked item's terms |

Contains information licensed under the Open Government Licence – Halifax.
Contains information licensed under the Open Government License – City of Surrey.
Contains information licensed under the Open Government Licence - The Corporation
of the City of Kitchener. No municipal endorsement is implied.

Native source geometry, selected source attributes, record IDs, exact filters,
retrieval timestamps, source-record checksums and attribution are retained.
Kitchener's crossing lines become length-weighted display/routing points, with
the original line preserved in `source_geometry`. Five Surrey records lack a
facility ID: their municipal `OBJECTID` is explicitly flagged as snapshot-scoped,
not a guaranteed permanent entity ID. Only duplicate asset IDs with otherwise
identical selected attributes and point geometry within 1 cm are collapsed;
duplicate-source evidence is retained. No 20-metre proximity suppression remains.

The builder enumerates ArcGIS object IDs and checks every batch. Missing records,
changed classifications, unknown statuses, bad geometry and conflicting asset
IDs fail the build before replacing the snapshot. Review source changes instead
of adding a fallback. See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for researched
sources, pending licence checks and coverage gaps; the national portal list is
not an exhaustive completed dataset audit.

Rebuild with Python 3.11+ (standard library only; no PBFs or osmium required):

```sh
python3 build-canada-raised-crosswalks.py \
  --output canada-raised-crosswalks.geojson
python3 -m unittest -v test_raised_crosswalks.py
```

The file and icon are consumed through these stable raw URLs:

```text
https://raw.githubusercontent.com/ammil-industries/aportee-datasets/main/canada-raised-crosswalks.geojson
https://raw.githubusercontent.com/ammil-industries/aportee-datasets/main/canada-raised-crosswalks.svg
```

Updating this source does not remove points from previously built tiles. Merge
the reviewed source change, rebuild the custom dataset's routing/POI artifacts,
and publish the replacement together so both dots and accessibility results
use the municipal-only snapshot. Do not reuse the old OSM-containing artifacts.

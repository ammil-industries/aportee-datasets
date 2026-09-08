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
inventory. It combines openly licensed municipal records that explicitly call
a feature a raised crosswalk with a strict OpenStreetMap fallback. An OSM
feature is included only when it has `traffic_calming=table` and either
`highway=crossing` or `footway=crossing`; ordinary speed tables, speed humps,
and raised intersections are excluded.

The current authoritative source is Halifax Regional Municipality's
[Traffic Calming Infrastructure](https://data-hrm.hub.arcgis.com/datasets/traffic-calming-infrastructure)
layer, filtered to installed assets with code `RSDCRW`. The fallback uses the
13 provincial and territorial Canada extracts published by
[Geofabrik](https://download.geofabrik.de/north-america/canada.html) under the
[OpenStreetMap ODbL](https://www.openstreetmap.org/copyright). Municipal records
take precedence over OSM features within 20 metres. Source IDs, evidence class,
licence, snapshot timestamps, and the exact counts are retained in the file.

Rebuild the snapshot with `osmium-tool` installed:

```sh
python3 build-canada-raised-crosswalks.py \
  --pbf-dir /path/to/provincial-osm-extracts \
  --output canada-raised-crosswalks.geojson
```

The file and icon are consumed through these stable raw URLs:

```text
https://raw.githubusercontent.com/ammil-industries/aportee-datasets/main/canada-raised-crosswalks.geojson
https://raw.githubusercontent.com/ammil-industries/aportee-datasets/main/canada-raised-crosswalks.svg
```

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

After updating the file, rerun the reviewed custom-access definition and publish
the resulting development tileset. Updating this repository alone does not
change the website.

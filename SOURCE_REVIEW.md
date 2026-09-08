# Canada raised-crosswalk source review

Reviewed 8 September 2026. **This is not an audit of every Canadian open-data
portal or every dataset within each reviewed municipality.** Layer schemas,
domains/subtypes and returned records were inspected for the sources below.
Public availability alone is not evidence of redistribution permission.
Municipal classification is not independent site/imagery verification.

## Inclusion policy and accepted sources

The dataset accepts only municipal inventory records explicitly classifying the
feature as a raised pedestrian crossing, with an in-service status and reviewed
reuse terms. OSM records are excluded entirely, not retained at lower confidence.
No ordinary crosswalk, speed table, raised intersection or textured pavement is
promoted to a raised crosswalk by inference. The builder's source allowlist is
the executable inclusion policy; this ledger records the wider research scope.

| Municipality | Exact municipal evidence | Source records | Current decision |
|---|---|---:|---|
| [Halifax](https://services2.arcgis.com/11XBiaBYA9Ep0yNJ/arcgis/rest/services/Traffic_Calming_Infrastructure/FeatureServer/0) | `ASSETCODE='RSDCRW' AND ASSETSTAT='INS'` | 10 | Included; existing adapter, rechecked |
| [Surrey](https://gisservices.surrey.ca/arcgis/rest/services/OpenData/MapServer/116) | `DEVICE_TYPE2='Raised Crossing' AND STATUS='In Service'` | 68 | Included as 67 features; one duplicated asset ID and near-identical point. Five missing facility IDs use flagged service record IDs |
| [Kitchener](https://services1.arcgis.com/qAo1OsXi67t7XgmS/arcgis/rest/services/Traffic_Calming/FeatureServer/0) | `CATEGORY='RAISED CROSSWALK' AND STATUS='ACTIVE'` | 37 | Included; preserve source polyline and derive point |
| [City of North Vancouver](https://gisext2.cnv.org/arcgis/rest/services/BaseMapServices/TransportMAP/MapServer/150) | `FEATURE_SUBTYPE IN (108,109) AND RAISED_FEATURE='True' AND STATUS='Existing'` | 23 | Not included: redistribution terms not verified. City is distinct from District of North Vancouver |
| [Saanich](https://map.saanich.ca/server/rest/services/MAPS/SaanichMapService_External/MapServer/126) | `MARKINGTYPE='R'`; domain explicitly defines R as Raised | 4 | Not included: redistribution terms and in-service status unverified; exposed layer has no status field |
| [Conception Bay South](https://services5.arcgis.com/4cgpd6caJYuDiTSW/arcgis/rest/services/Active_Traffic_Calming_Location/FeatureServer/0) | `Type='Raised Crosswalk'` in active inventory | 1 | Not included: redistribution terms not verified; public ArcGIS item's licence field is empty |

Surrey's map legend says “Raised Crosswalk” but the stored value is “Raised
Crossing.” Querying only the legend label misses the records. North Vancouver's
raised flag also describes non-crosswalk assets; the crosswalk subtype filter
is essential. Four Conception Bay South “Textured Crosswalk” records were not
assumed raised. These examples require city-specific mappings, not a national
keyword query.

## Inspected layers without a usable direct raised-crosswalk classification

These are **layer-specific findings, not claims that the city has no raised
crosswalks or that no other municipal source exists**.

| Municipality / inspected source | Finding | Remaining work |
|---|---|---|
| [Victoria traffic calming](https://maps.victoria.ca/server/rest/services/OpenData/OpenData_Transportation/MapServer/30) and [crosswalks](https://maps.victoria.ca/server/rest/services/OpenData/OpenData_Transportation/MapServer/18) | No explicit raised-crosswalk class in inspected traffic-calming values; all 171 crosswalk records have a generic crosswalk type | Find physical crossing/engineering asset attributes; do not infer from speed humps or sidewalk extensions |
| [Burnaby traffic calming](https://gis.burnaby.ca/arcgis/rest/services/OpenData/OpenData5/MapServer/3) | Actual TYPE values include 450–490, but published renderer only explains 400–440 and field domains are null | Obtain the missing codebook; this remains a promising unresolved lead |
| [Toronto traffic-calming database](https://open.toronto.ca/dataset/traffic-calming-database/) | 1,227 street-segment records with counts of islands, humps, cushions and bumps; no raised-crosswalk field | Locate crossing-level physical asset data; segment counts cannot provide crossing point locations |
| [Ottawa pedestrian crossovers](https://maps.ottawa.ca/arcgis/rest/services/ActiveTransportation/MapServer/1) | 159 PXO records; B/C/D codes describe traffic-control arrangements, not elevation; no dedicated raised field | Other engineering/traffic-calming layers and project-completion records remain to review |
| [Hamilton speed humps](https://services.arcgis.com/rYz782eMbySr2srL/arcgis/rest/services/Traffic_Speed_Humps/FeatureServer/12) and [pedestrian crossovers](https://www.arcgis.com/home/item.html?id=de2e122dcd824fcdacb8672b140f528b) | Hump types are Cushion, Permanent or Temporary. Crossover B/C/D types describe control equipment, not elevation | Seek explicit raised classification elsewhere; generic hump/PXO records excluded |
| [Calgary crosswalks](https://data.calgary.ca/Health-and-Safety/Crosswalks/hxgg-rpad) | Inspected markings schema records type, paint/material and components, not a dedicated physical raised flag | Other Calgary crosswalk-location and asset layers have not been fully audited |
| [Repentigny traffic-calming measures](https://www.donneesquebec.ca/recherche/dataset/mesure-d-apaisement-de-la-circulation) | 220 features include 10 explicitly raised intersections, not explicitly raised crosswalks | Preserve raised intersections as a separate concept; not included here |
| [Whitehorse traffic-calming layer](https://services2.arcgis.com/QMlsE6M1PZEGt8Zf/arcgis/rest/services/TrafficCalmingShapeFile/FeatureServer/0) | Road eligibility/request/implementation programme lines, not a typed physical device inventory | Find asset inventory or as-built records |

## Discovery only / incomplete review

Searches also investigated Vancouver, Edmonton, Montréal, Laval, Québec City,
Guelph, Maple Ridge, Winnipeg, Moncton, Fredericton and Waterloo-region leads.
They have **not** had a comprehensive schema-and-record audit across their
catalogues. Examples found include surveys, programme policies, project pages,
generic road/walkway layers and proposed installations; none were admitted as
municipal-recorded in-service raised-crosswalk evidence from those searches.

The next high-value steps are Burnaby's missing type dictionary; reuse/status
verification for the three positive-but-held sources; deeper traffic-engineering
asset searches for Victoria and the other partially reviewed cities; and a
systematic province-by-province portal audit. A portal being listed does not
mean its catalogue has been inspected. No municipal contact has been made.

## Statistics Canada and the portal registry

The [2025 Canadian Pedestrian Network Database](https://www150.statcan.gc.ca/n1/pub/34-26-0004/342600042025001-eng.htm)
is useful for source discovery and pedestrian context, not a ready raised-crosswalk
inventory. Inspection of the downloadable archive found 1,710,855 features,
including 5,092 classified as Crosswalk, but no dedicated raised flag or asset
status column. No source-class string contained “raised” or “surélevé”; that is
not proof that no raised crossing exists among opaque or generic source codes.
The feature table has 53 municipality labels; its source register has 68 rows
covering 55 municipalities. The published report describes 66 input datasets;
the archive/register discrepancy is retained rather than silently reconciled.

The supplied attribution list (55 municipalities plus three national references),
the complete archive source register and [Statistics Canada's LODE portal master](https://github.com/CSBP-CPSE/LODE-ECDO/blob/master/MasterList_OpenDataPortals.csv)
(111 rows) have been retained in a separate research registry: 123 normalized
jurisdiction/organization entries and 346 distinct links before the latest
licence checks. These are discovery seeds, **not 123 completed municipal audits**
and not an exhaustive census of all Canadian portals. Dataset, portal and licence
links have distinct roles; historic “updated” years are not fresh verification dates.

Known source-register issues include a Maple Ridge row linking to Milton,
an expired signed Kawartha Lakes download, a non-URL “Request Permission” entry
for Greater Sudbury, and confusing City vs District of North Vancouver. These
must not be ingested automatically. Signed query credentials were stripped from
the reusable registry. Raw API evidence, queries and retrieval hashes are saved
in the aportee workspace under
`exa-results/canada-raised-crosswalks-2026-09-08/`.

## Harmonization and matching

There is a conventional workflow, not one universal Canadian raised-crosswalk
code. [StatCan's methodology](https://www150.statcan.gc.ca/n1/pub/34-26-0004/2025001/meta-eng.htm)
likewise describes mapping municipal classifications with a data dictionary.
First harmonize semantics per source; only then match overlapping observations
of the same physical crossing. Different cities share a schema, not the same
physical entities.

Keep native geometry, source IDs, exact class/status assertions and attribution.
For future overlaps, shared asset IDs and crossing movement/road arm, orientation,
level and temporal status should support candidate matching. Distance alone is
not a match decision: opposite arms can be within 20 metres. Keep uncertain
matches for review and preserve both sources. The current municipal-only build
does not perform general cross-source conflation; it collapses only the narrowly
defined same-asset duplicate described above.

Adding a municipal crossing as a custom destination also does not itself add
pedestrian network connectivity or change street crossing costs. Those are
separate routing-model interventions.

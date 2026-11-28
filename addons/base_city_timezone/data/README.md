# GeoNames cities

`geonames_cities15000.tsv` lists the cities of more than 15 000 inhabitants,
with their IANA timezone and coordinates. It is loaded into `res.city` when the
module is installed.

## Source and license

- Source: GeoNames, `cities15000.zip` from https://download.geonames.org/export/dump/
- Downloaded: 2026-11-17
- License: [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/),
  data by [GeoNames](https://www.geonames.org)

## Format

Tab-separated, UTF-8, one header line, sorted by `geonameid` so that refreshes
give readable diffs. It is the original file reduced to these columns (the
alternate names column alone makes up most of the original's size):

| Column | Original column | Content |
| --- | --- | --- |
| `geonameid` | 1 | GeoNames id, stored in `res.city.geonames_id` |
| `name` | 2 | name of the city |
| `asciiname` | 3 | name in plain ASCII |
| `latitude` | 5 | decimal degrees (WGS84) |
| `longitude` | 6 | decimal degrees (WGS84) |
| `country_code` | 9 | ISO 3166-1 alpha-2 |
| `admin1_code` | 11 | GeoNames code of the first-level division (state, region…), only used to match existing cities |
| `population` | 15 | number of inhabitants |
| `timezone` | 18 | IANA timezone name |

## Regenerating the file

From the module's `data/` directory:

```sh
curl -sSLO https://download.geonames.org/export/dump/cities15000.zip
{
  printf 'geonameid\tname\tasciiname\tlatitude\tlongitude\tcountry_code\tadmin1_code\tpopulation\ttimezone\n'
  unzip -p cities15000.zip cities15000.txt | cut -f1,2,3,5,6,9,11,15,18 | sort -t$'\t' -k1,1n
} > geonames_cities15000.tsv
rm cities15000.zip
```

Then update the download date above, and load the changes into an existing
database from an Odoo shell:

```python
env['res.city']._load_geonames_cities()
env.cr.commit()
```

Cities that disappeared from the file are not deleted.

# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Panama postal code decoding and reverse geocoding.

Panama's postal code (Sistema de Códigos Postales, Correos de Panamá / COTEL) is
not a zone code assigned per administrative division: it encodes a geographic
grid cell directly, anchored at (10°N, 83.5°W), with up to ~3.3m precision.
Decoding a code therefore yields GPS coordinates, not a corregimiento - finding
the corregimiento requires a point-in-polygon lookup against its boundary.

The grid algorithm below is pure arithmetic (not a copyrightable/redistributable
government dataset); it was independently re-derived to match the public
description of the official site's encoding scheme. The corregimiento/poblado/
barrio boundary polygons used for the lookup are stored on the `boundary` field
of those models (populated from the same public INEC/Correos de Panamá geodata
already used to build their name/code data), so the resolution works fully
offline against the database - no live calls to the government site at runtime.
"""
import json
from dataclasses import dataclass

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTVWXZ"  # base-30, excludes ambiguous 0/1/I/O/U/Y
ALPHA_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}

ORIGIN_LAT = 10.0
ORIGIN_LNG = -83.5

STEP_MACRO = 0.1425
STEP_MICRO = 0.1425 / 24
STEP_NANO = 0.0059375 / 25
STEP_PICO = 2375e-7 / 8

MACRO_COLS = 40
MICRO_COLS = 24
NANO_COLS = 25
PICO_COLS = 8

# Loose bounding box used by the official site to accept/reject a decoded point.
PANAMA_BBOX = (6.0, 11.0, -86.0, -74.0)  # lat_min, lat_max, lng_min, lng_max


@dataclass
class DecodedPostalCode:
    lat: float
    lng: float
    precision_meters: float
    level: str


def _decode_pair(pair):
    return ALPHA_INDEX[pair[0]] * 30 + ALPHA_INDEX[pair[1]]


def _normalize(code):
    """Strip separators/spaces, uppercase, and split off the estafeta prefix.

    Returns (body, prefix) where body has length 2/4/6/8, or (None, None) if
    the code isn't well-formed.
    """
    if not code:
        return None, None
    clean = code.replace('-', '').replace(' ', '').upper()
    if not clean or len(clean) > 10 or any(ch not in ALPHA_INDEX for ch in clean):
        return None, None
    if len(clean) == 10:
        return clean[2:], clean[:2]
    if len(clean) % 2:
        return None, None
    return clean, None


def decode_postal_code(code):
    """Decode a Panama postal code to (lat, lng) of its grid cell center.

    Accepts codes with or without the 2-character estafeta prefix, and with or
    without separators (e.g. "ACC99-PJ42W", "ACC99PJ42W", "M9C9AG4434").
    Returns None if the code is malformed.
    """
    body, _prefix = _normalize(code)
    if not body:
        return None

    macro = _decode_pair(body[0:2])
    macro_row, macro_col = divmod(macro, MACRO_COLS)
    lat = ORIGIN_LAT - macro_row * STEP_MACRO - STEP_MACRO / 2
    lng = ORIGIN_LNG + macro_col * STEP_MACRO + STEP_MACRO / 2
    level, precision = 'macro', STEP_MACRO

    if len(body) >= 4:
        micro = _decode_pair(body[2:4])
        micro_row, micro_col = divmod(micro, MICRO_COLS)
        base_lat = ORIGIN_LAT - macro_row * STEP_MACRO
        base_lng = ORIGIN_LNG + macro_col * STEP_MACRO
        lat = base_lat - micro_row * STEP_MICRO - STEP_MICRO / 2
        lng = base_lng + micro_col * STEP_MICRO + STEP_MICRO / 2
        level, precision = 'micro', STEP_MICRO

    if len(body) >= 6:
        nano = _decode_pair(body[4:6])
        nano_row, nano_col = divmod(nano, NANO_COLS)
        base_lat = ORIGIN_LAT - macro_row * STEP_MACRO - micro_row * STEP_MICRO
        base_lng = ORIGIN_LNG + macro_col * STEP_MACRO + micro_col * STEP_MICRO
        lat = base_lat - nano_row * STEP_NANO - STEP_NANO / 2
        lng = base_lng + nano_col * STEP_NANO + STEP_NANO / 2
        level, precision = 'nano', STEP_NANO

    if len(body) >= 8:
        pico = _decode_pair(body[6:8])
        pico_row, pico_col = divmod(pico, PICO_COLS)
        base_lat = ORIGIN_LAT - macro_row * STEP_MACRO - micro_row * STEP_MICRO - nano_row * STEP_NANO
        base_lng = ORIGIN_LNG + macro_col * STEP_MACRO + micro_col * STEP_MICRO + nano_col * STEP_NANO
        lat = base_lat - pico_row * STEP_PICO - STEP_PICO / 2
        lng = base_lng + pico_col * STEP_PICO + STEP_PICO / 2
        level, precision = 'pico', STEP_PICO

    return DecodedPostalCode(lat=lat, lng=lng, precision_meters=round(precision * 111_000, 2), level=level)


def is_in_panama(lat, lng):
    lat_min, lat_max, lng_min, lng_max = PANAMA_BBOX
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max


def _point_in_ring(lng, lat, ring):
    """Ray casting point-in-polygon test. `ring` is a closed [lng, lat] list."""
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lng, lat, polygon):
    if not polygon or not _point_in_ring(lng, lat, polygon[0]):
        return False
    return not any(_point_in_ring(lng, lat, hole) for hole in polygon[1:])


def _boundary_contains(lng, lat, boundary_json):
    """`boundary_json` is the raw string from a record's `boundary` field."""
    if not boundary_json:
        return False
    geometry = json.loads(boundary_json)
    geom_type = geometry.get('type')
    coordinates = geometry.get('coordinates')
    if geom_type == 'Polygon':
        return _point_in_polygon(lng, lat, coordinates)
    if geom_type == 'MultiPolygon':
        return any(_point_in_polygon(lng, lat, polygon) for polygon in coordinates)
    return False


def _find_record(records, lat, lng):
    """Return the first record in `records` whose `boundary` contains (lat, lng)."""
    for record in records:
        if _boundary_contains(lng, lat, record.boundary):
            return record
    return records.browse()


def locate_postal_code(env, code):
    """Decode `code` and resolve it down to corregimiento/poblado/barrio records.

    Each level is only searched within the previous one's boundary (scoped by
    its `corregimiento_id`/`poblado_id`), so this never scans the full 13k+
    poblados or 3.6k barrios of the country.

    Returns a dict {'lat', 'lng', 'precision_meters', 'level', 'corregimiento',
    'poblado', 'barrio'} (the latter three are empty recordsets as soon as one
    level isn't found), or None if the code is malformed or falls outside Panama.
    """
    decoded = decode_postal_code(code)
    if decoded is None or not is_in_panama(decoded.lat, decoded.lng):
        return None
    lat, lng = decoded.lat, decoded.lng

    result = {
        'lat': lat,
        'lng': lng,
        'precision_meters': decoded.precision_meters,
        'level': decoded.level,
        'corregimiento': env['l10n_pa.res.city.corregimiento'],
        'poblado': env['l10n_pa.res.city.corregimiento.poblado'],
        'barrio': env['l10n_pa.res.city.corregimiento.poblado.barrio'],
    }

    corregimientos = env['l10n_pa.res.city.corregimiento'].search([('boundary', '!=', False)])
    corregimiento = _find_record(corregimientos, lat, lng)
    result['corregimiento'] = corregimiento
    if not corregimiento:
        return result

    poblados = env['l10n_pa.res.city.corregimiento.poblado'].search([
        ('corregimiento_id', '=', corregimiento.id),
        ('boundary', '!=', False),
    ])
    poblado = _find_record(poblados, lat, lng)
    result['poblado'] = poblado
    if not poblado:
        return result

    barrios = env['l10n_pa.res.city.corregimiento.poblado.barrio'].search([
        ('poblado_id', '=', poblado.id),
        ('boundary', '!=', False),
    ])
    result['barrio'] = _find_record(barrios, lat, lng)
    return result

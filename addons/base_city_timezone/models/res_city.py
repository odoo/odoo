# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import csv
import logging
import unicodedata

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import file_open
from odoo.tools.date_utils import all_timezones

_logger = logging.getLogger(__name__)

GEONAMES_FILE = 'base_city_timezone/data/geonames_cities15000.tsv'
CREATE_BATCH_SIZE = 1000


# letters that NFKD does not decompose into a base letter + accent
_LATIN_LETTERS = str.maketrans({
    'ø': 'o', 'Ø': 'o', 'æ': 'ae', 'Æ': 'ae', 'œ': 'oe', 'Œ': 'oe', 'ß': 'ss',
    'ł': 'l', 'Ł': 'l', 'đ': 'd', 'Đ': 'd', 'ð': 'd', 'Ð': 'd', 'þ': 'th', 'Þ': 'th', 'ı': 'i',
})


def _normalize(name):
    """Strip accents, ignore case and punctuation-like separators."""
    name = unicodedata.normalize('NFKD', (name or '').translate(_LATIN_LETTERS))
    name = ''.join(c for c in name if not unicodedata.combining(c))
    return ' '.join(name.replace('-', ' ').replace("'", ' ').casefold().split())


class ResCity(models.Model):
    _inherit = 'res.city'

    tz = fields.Selection(_tz_get, string='Timezone')
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    geonames_id = fields.Integer("GeoNames ID", copy=False, readonly=True)  # indexed by the constraint

    _geonames_id_unique = models.Constraint(
        'unique(geonames_id)',
        "A GeoNames city can only be loaded once.",
    )

    @api.model
    def _get_city_timezone(self, country, city_name, state=None):
        """Return the timezone of the city called ``city_name`` in ``country``.

        Names are compared without accents nor case. If several cities have
        that name, ``state`` narrows them down when it can (cities loaded from
        GeoNames have no state); the cities left must agree on the timezone.

        :param country: ``res.country`` record
        :param city_name: name of the city, as typed in an address
        :param state: optional ``res.country.state`` record
        :returns: the timezone name, or ``False`` if the city is unknown or ambiguous
        """
        if not country or not city_name:
            return False
        name = _normalize(city_name)
        cities = [
            city
            for city in self.sudo().with_context(lang='en_US').search_read(
                [('country_id', '=', country.id), ('tz', '!=', False)], ['name', 'tz', 'state_id'],
            )
            if _normalize(city['name']) == name
        ]
        if state and (in_state := [c for c in cities if c['state_id'] and c['state_id'][0] == state.id]):
            cities = in_state
        timezones = {city['tz'] for city in cities}
        return timezones.pop() if len(timezones) == 1 else False

    @api.model
    def _load_geonames_cities(self):
        """Create or update the cities of the GeoNames file.

        - Cities already loaded (same ``geonames_id``) get their timezone and
          coordinates updated.
        - Cities created by other modules (e.g. localizations) are completed
          instead of duplicated when they match unambiguously: same country,
          same name and same state code (GeoNames' admin1 code), or same
          country and a name that is unique on both sides.
        - Other cities are created, without state: GeoNames' admin1 codes do
          not match Odoo's state codes in general.

        Can be called again after refreshing the data file.
        """
        Cities = self.with_context(lang='en_US', active_test=False)
        countries = {
            country['code']: country['id']
            for country in self.env['res.country'].search_read([], ['code'])
        }

        loaded = {
            city['geonames_id']: city
            for city in Cities.search_read(
                [('geonames_id', '!=', False)], ['geonames_id', 'tz', 'latitude', 'longitude'],
            )
        }

        # cities from other sources, indexed for matching
        by_state = collections.defaultdict(list)
        by_name = collections.defaultdict(list)
        for city in Cities.search([('geonames_id', '=', False)]):
            name = _normalize(city.name)
            by_state[city.country_id.id, name, city.state_id.code].append(city.id)
            by_name[city.country_id.id, name].append((city.id, city.state_id.code))

        with file_open(GEONAMES_FILE) as file:
            rows = [
                row for row in csv.DictReader(file, delimiter='\t', quoting=csv.QUOTE_NONE)
                if row['country_code'] in countries
            ]
        names_in_file = collections.Counter(
            (row['country_code'], _normalize(row['name'])) for row in rows
        )
        admin1_codes = collections.defaultdict(set)
        for row in rows:
            admin1_codes[row['country_code']].add(row['admin1_code'])

        to_create = []
        to_write = {}  # city id: vals
        matched = set()
        skipped_tz = 0
        for row in rows:
            tz = row['timezone']
            if tz not in all_timezones:
                skipped_tz += 1
                tz = False
            vals = {
                'tz': tz,
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
            }
            geonames_id = int(row['geonameid'])

            if city := loaded.get(geonames_id):
                if any(city[key] != value for key, value in vals.items()):
                    to_write[city['id']] = vals
                continue

            country_id = countries[row['country_code']]
            name = _normalize(row['name'])
            candidates = by_state.get((country_id, name, row['admin1_code']), [])
            if len(candidates) != 1 and names_in_file[row['country_code'], name] == 1:
                # same name, unique on both sides; but if the city's state code
                # is one GeoNames uses for this country (e.g. US), the codes are
                # comparable and differ, so it is another city
                candidates = [
                    city_id
                    for city_id, state_code in by_name.get((country_id, name), [])
                    if not state_code or state_code not in admin1_codes[row['country_code']]
                ]
            if len(candidates) == 1 and candidates[0] not in matched:
                matched.add(candidates[0])
                to_write[candidates[0]] = {**vals, 'geonames_id': geonames_id}
                continue

            to_create.append({
                **vals,
                'name': row['name'],
                'country_id': country_id,
                'geonames_id': geonames_id,
            })

        for city_id, vals in to_write.items():
            Cities.browse(city_id).write(vals)
        for start in range(0, len(to_create), CREATE_BATCH_SIZE):
            Cities.create(to_create[start:start + CREATE_BATCH_SIZE])

        _logger.info(
            "GeoNames cities: %d created, %d existing cities completed, %d updated, "
            "%d without a known timezone",
            len(to_create), len(matched), len(to_write) - len(matched), skipped_tz,
        )

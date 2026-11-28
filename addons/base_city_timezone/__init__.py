# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _load_geonames_cities(env):
    env['res.city']._load_geonames_cities()

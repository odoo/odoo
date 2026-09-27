# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv

# Some corregimiento boundary polygons (data/l10n_pa.res.city.corregimiento.csv,
# 'boundary' column) are encoded as GeoJSON strings above Python's default 128KB
# csv field limit. Raise it before any CSV in this module gets loaded; this only
# widens what csv.reader() accepts, it never restricts anything.
if csv.field_size_limit() < 5_000_000:
    csv.field_size_limit(5_000_000)

from . import demo
from . import models
from . import tools

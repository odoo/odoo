# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re


PRODUCT_FEED_SOFT_LIMIT = 5000
PRODUCT_FEED_HARD_LIMIT = 6000

# Google Merchant Center
GMC_SUPPORTED_UOM = {
    'oz',
    'lb',
    'mg',
    'g',
    'kg',
    'floz',
    'pt',
    'ct',
    'qt',
    'gal',
    'ml',
    'cl',
    'l',
    'cbm',
    'in',
    'ft',
    'yd',
    'cm',
    'm',
    'sqft',
    'sqm',
}
GMC_BASE_MEASURE = re.compile(r'(?P<base_count>\d+)?\s*(?P<base_unit>[a-z]+)')

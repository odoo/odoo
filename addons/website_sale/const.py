import re

GMC_SUPPORTED_UOM = {
    'oz',
    'lb',
    'mg',
    'g',
    'kg',
    'floz',
    'pt',
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

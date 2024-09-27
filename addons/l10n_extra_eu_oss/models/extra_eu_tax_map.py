"""
Tax map for non EU countries that want to use the OSS system.

it takes the form tuple: rate, where
    (Fiscal Country Code, Domestic Tax Rate, Foreign Country Code): Foreign Tax Rate
"""

EXTRA_EU_TAX_MAP = {
    ('GB', 20.0, 'AT'): 20.0,
    ('GB', 20.0, 'BE'): 21.0,
    ('GB', 20.0, 'BG'): 20.0,
    ('GB', 20.0, 'CY'): 19.0,
    ('GB', 20.0, 'CZ'): 21.0,
    ('GB', 20.0, 'DE'): 19.0,
    ('GB', 20.0, 'DK'): 25.0,
    ('GB', 20.0, 'EE'): 22.0,
    ('GB', 20.0, 'ES'): 21.0,
    ('GB', 20.0, 'FI'): 24.0,
    ('GB', 20.0, 'FR'): 20.0,
    ('GB', 20.0, 'HR'): 25.0,
    ('GB', 20.0, 'HU'): 27.0,
    ('GB', 20.0, 'IE'): 23.0,
    ('GB', 20.0, 'IT'): 22.0,
    ('GB', 20.0, 'LT'): 21.0,
    ('GB', 20.0, 'LU'): 16.0,
    ('GB', 20.0, 'LV'): 21.0,
    ('GB', 20.0, 'MT'): 18.0,
    ('GB', 20.0, 'NL'): 21.0,
    ('GB', 20.0, 'PL'): 23.0,
    ('GB', 20.0, 'PT'): 23.0,
    ('GB', 20.0, 'RO'): 19.0,
    ('GB', 20.0, 'SE'): 25.0,
    ('GB', 20.0, 'SI'): 22.0,
    ('GB', 20.0, 'SK'): 20.0,
}

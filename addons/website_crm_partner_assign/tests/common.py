from unittest.mock import patch


def patch_geo_find():
    """Returns a patch object that replaces geo_find with a fake function."""
    def fake_geo_find(addr, **kw):
        return {
            'Wavre, Belgium': (50.7158956, 4.6128075),
            'Cannon Hill Park, B46 3AG Birmingham, United Kingdom': (52.45216, -1.898578),
            'Gandhinagar, Gujarat, India': (23.1933118, 72.6348905),
        }.get(addr)

    return patch(
        'odoo.addons.base_geolocalize.models.base_geocoder.BaseGeocoder.geo_find',
        wraps=fake_geo_find
    )

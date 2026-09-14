{
    "name": "Geocoding",
    "version": "3.1",
    "category": "Hidden",
    "description": """
Geocoding
=========
Convert addresses into GPS coordinates, and coordinates back into place names,
through a pluggable provider.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/geocoder_provider_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "data/data.xml",
    ],
}

{
    'name': 'Website Google Map',
    'category': 'Hidden',
    'summary': '',
    'version': '1.0',
    'description': """
OpenERP Website Google Map
========================

        """,
    'author': 'OpenERP SA',
    'depends': ['base_geolocalize', 'website_partner'],
    'data': [
        'views/google_map.xml',
    ],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Extended Addresses with OpenStreetMap',
    'summary': 'Add extra fields on addresses and integrate OpenStreetMap for geolocation',
    'sequence': 19,
<<<<<<< HEAD
    'version': '1.1',
    'category': 'Hidden',
=======
    'version': '2.0',
    'category': 'Sales/Sales',
>>>>>>> 5ec06c51f0d1 (update contactos y cuentas)
    'description': """
Extended Addresses Management with OpenStreetMap Integration
============================================================

This module provides the ability to choose a city from a list (in specific countries)
and integrates OpenStreetMap (OSM) for automatic geolocation of partners.

Features:
- Extended address fields with city selection
- Automatic geocoding using OpenStreetMap Nominatim API
- Interactive maps showing partner locations
- Bulk geocoding of existing partners
- Geolocation filters in partner lists

It is primarily used for EDIs that might need a special city code.
    """,
    'data': [
        'security/ir.model.access.csv',
        'views/base_address_extended.xml',
        'views/res_city_view.xml',
        'views/res_country_view.xml',
        'views/res_partner_map_views.xml',
    ],
<<<<<<< HEAD
    'depends': ['base', 'contacts'],
=======
    'assets': {
        'web.assets_backend': [
            'base_address_extended/static/src/js/partner_map_handler.js',
        ],
    },
    'external_dependencies': {
        'python': ['requests'],
    },
    'depends': ['base', 'contacts', 'web'],
    'author': 'Odoo S.A.',
>>>>>>> 5ec06c51f0d1 (update contactos y cuentas)
    'license': 'LGPL-3',
    'installable': True,
}

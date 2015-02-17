# -*- coding: utf-8 -*-

{
    'name': 'Website Google Map',
    'category': 'Hidden',
    'summary': '',
    'version': '1.0',
    'description': """
Odoo Website Google Map
==========================

        """,
    'author': 'Odoo S.A.',
    'depends': ['base_geolocalize', 'website_partner', 'crm_partner_assign'],
    'data': [
        'views/google_map_templates.xml',
    ],
    'installable': True,
}

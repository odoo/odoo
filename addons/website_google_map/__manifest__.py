# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Google Maps',
    'category': 'Website/Website',
    'summary': 'Show your company address on Google Maps',
    'version': '1.0',
    'description': """
Show your company address/partner address on Google Maps. Configure an API key in the Website settings.
    """,
    'depends': ['base_geolocalize', 'website_partner'],
    'data': [
        'views/google_map_templates.xml',
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

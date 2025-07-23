# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Partner',
    'category': 'Website/Website',
    'summary': 'Partner module for website',
    'version': '0.1',
    'description': """
This is a base module. It holds website-related stuff for Contact model (res.partner).
    """,
    'depends': [
        'contacts',
        'website',
    ],
    'data': [
        'views/res_partner_views.xml',
        'views/website_partner_templates.xml',
        'data/website_partner_data.xml',
        'views/snippets.xml',
    ],
    'demo': ['data/website_partner_demo.xml'],
    'installable': True,
    'assets': {
        'website.website_builder_assets': [
            'website_partner/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

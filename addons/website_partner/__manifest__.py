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
        'base_geolocalize',
        'contacts',
        'partnership',
        'website',
    ],
    'data': [
        'views/res_partner_views.xml',
        'views/website_partner_templates.xml',
        'data/website_partner_data.xml',
        'data/res_partner_activation_data.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/res_partner_grade_views.xml',
        'views/res_partner_activation_views.xml',
        'views/partner_assign_menus.xml',
        'views/res_partner_views_copy.xml',
        'views/snippets.xml',
    ],
    'demo': [
        'data/website_partner_demo.xml',
        'data/res_partner_grade_demo.xml',
        'data/res_partner_demo.xml',
    ],
    'installable': True,
    'assets': {
        'website.website_builder_assets': [
            'website_partner/static/src/website_builder/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

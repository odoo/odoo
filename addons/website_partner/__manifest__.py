# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Partner',
    'category': 'Website',
    'summary': 'Partner Module for Website',
    'version': '0.1',
    'description': """Base module holding website-related stuff for partner model""",
    'depends': ['website'],
    'data': [
        'views/res_partner_views.xml',
        'views/website_partner_templates.xml',
        'data/website_partner_data.xml',
    ],
    'demo': ['data/website_partner_demo.xml'],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Online Members Directory',
    'category': 'Website/Website',
    'summary': 'Publish your members directory',
    'version': '1.0',
    'description': """
Publish your members/association directory publicly.
    """,
    'depends': ['website_partner', 'website_google_map', 'association', 'website_sale'],
    'data': [
        'views/product_template_views.xml',
        'views/website_membership_templates.xml',
        'security/ir.model.access.csv',
        'security/website_membership.xml',
        'views/snippets.xml',
    ],
    'demo': ['data/membership_demo.xml'],
    'installable': True,
    'license': 'LGPL-3',
}

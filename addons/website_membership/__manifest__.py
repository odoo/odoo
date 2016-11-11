# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Associations: Members',
    'summary': 'Online Directory of Members',
    'category': 'Website',
    'summary': 'Publish Associations, Groups and Memberships',
    'version': '1.0',
    'description': """
Website for browsing Associations, Groups and Memberships
=========================================================
""",
    'depends': ['website_partner', 'website_google_map', 'association', 'website_sale'],
    'data': [
        'views/website_membership_templates.xml',
        'security/ir.model.access.csv',
        'security/website_membership.xml',
    ],
    'demo': ['data/membership_demo.xml'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

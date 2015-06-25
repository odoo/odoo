# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Associations: Members',
    'summary': 'Online Directory of Members',
    'category': 'Website',
    'summary': 'Publish Associations, Groups and Memberships',
    'description': """
Website for browsing Associations, Groups and Memberships
=========================================================
""",
    'depends': ['website_partner', 'website_google_map', 'association', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_membership_security.xml',
        'views/website_membership_templates.xml',
    ],
    'demo': ['demo/membership.xml'],
}

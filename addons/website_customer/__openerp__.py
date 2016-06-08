# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer References',
    'category': 'Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'summary': 'Publish Your Customer References',
    'version': '1.0',
    'description': """
Odoo Customer References
===========================
""",
    'depends': [
        'crm_partner_assign',
        'website_partner',
        'website_google_map',
    ],
    'demo': [
        'data/res_partner_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/res_partner_tag_security.xml',
        'views/website_customer_templates.xml',
        'views/res_partner_views.xml',

    ],
    'qweb': [],
    'installable': True,
}

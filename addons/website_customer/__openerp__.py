# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer References',
    'category': 'Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'summary': 'Publish Your Customer References',
    'version': '1.0',
    'description': """
OpenERP Customer References
===========================
""",
    'depends': [
        'crm_partner_assign',
        'website_partner',
        'website_google_map',
    ],
    'demo': [
        'website_customer_demo.xml',
    ],
    'data': [
        'views/website_customer.xml',
        'views/website_customer_view.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
    ],
    'qweb': [],
    'installable': True,
}

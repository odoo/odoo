# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Portal for Sales',
    'category': 'Website',
    'summary': 'Add your sales document in the frontend portal (sales order, quotations, invoices)',
    'version': '1.0',
    'description': """
Add your sales document in the frontend portal. Your customers will be able to connect to their portal to see the list (and the state) of their invoices (pdf report), sales orders and quotations (web pages).
        """,
    'depends': [
        'portal_sale',
        'website_portal',
        'website_payment',
        'portal',
    ],
    'data': [
        'views/website_portal_sale_templates.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/sale_demo.xml'
    ],
    'installable': True,
}

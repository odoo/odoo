# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Portal for Sales',
    'category': 'Website',
    'summary': 'Add your sales document in the frontend portal (sales order, quotations)',
    'version': '1.0',
    'description': """
Add your sales document in the frontend portal. Your customers will be able to connect to their portal to see the list (and the state) of their sales orders and quotations (web pages).
        """,
    'depends': [
        'sale',
        'sale_payment',
        'website_portal',
        'website_payment',
    ],
    'data': [
    ],
    'demo': [
    ],
    'installable': True,
}

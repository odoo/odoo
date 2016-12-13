# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Management',
    'category': 'Sales',
    'sequence': 15,
    'summary': 'Quotations, Sales Orders, Invoicing',
    'description': """
This application gives you a quick view of your Quotation, Sales order, Invoice, accessible from your home page.
You can track your sales goals in an effective and efficient manner by keeping track of all sales orders and history.
    """,
    'website': 'https://www.odoo.com/page/sales',
    'depends': ['sale'],
    'data': [
        'security/sale_salesman_security.xml',
        'views/sale_views.xml',
    ],
    'application': True,
}

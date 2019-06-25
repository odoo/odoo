# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Sale Report(GST)',
    'version': '1.0',
    'description': """GST Sale Report""",
    'category': 'Accounting',
    'depends': [
        'l10n_in',
        'sale',
    ],
    'data': [
        'data/product_demo.xml',
        'views/report_sale_order.xml',
        'views/sale_views.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}

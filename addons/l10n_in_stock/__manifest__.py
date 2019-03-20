# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Stock Report(GST)',
    'version': '1.0',
    'description': """GST Stock Report""",
    'category': 'Accounting',
    'depends': [
        'l10n_in',
        'stock',
    ],
    'data': [
        'data/product_demo.xml',
        'views/report_stockpicking_operations.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}

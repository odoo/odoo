# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Sale Report(GST)',
    'countries': ['in'],
    'version': '1.0',
    'description': """GST Sale Report""",
    'category': 'Accounting/Localizations/Sale',
    'depends': [
        'l10n_in',
        'sale',
    ],
    'data': [
        'views/report_sale_order.xml',
        'views/sale_views.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

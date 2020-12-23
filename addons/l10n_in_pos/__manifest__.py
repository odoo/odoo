# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Point of Sale',
    'version': '1.0',
    'description': """GST Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_in',
        'point_of_sale'
    ],
    'data': [
        'views/point_of_sale.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'qweb': [
        'static/src/xml/pos_receipt.xml',
    ],
    'auto_install': True,
}

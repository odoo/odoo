# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "India Purchase and Warehouse Management",

    'summary': "Get warehouse address if the bill is created from Purchase Order",

    'description': """
Get the warehouse address if the bill is created from the Purchase Order

So this module is to get the warehouse address if the bill is created from Purchase Order
    """,

    'website': "https://www.odoo.com",
    'category': 'Accounting/Localizations/Purchase',
    'version': '1.0',

    'depends': [
        'l10n_in_purchase',
        'l10n_in_stock',
        'purchase_stock'
    ],

    'auto_install': True,
    'license': 'LGPL-3',
}

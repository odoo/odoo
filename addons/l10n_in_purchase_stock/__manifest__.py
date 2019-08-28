# -*- coding: utf-8 -*-
{
    'name': "India Purchase and Warehouse Management",

    'summary': """
        Define default purchase journal on the warehouse""",

    'description': """
        Define default purchase journal on the warehouse,
        help you to choose correct purchase journal on the purchase order when
        you change the picking operation.

        useful when you setup the multiple gstn units.
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com",
    'category': 'Localization',
    'version': '0.1',

    'depends': ['l10n_in_purchase', 'l10n_in_stock'],

    'data': [
        'views/stock_views.xml'
    ],
    'demo': [

    ],
    'auto_install': True
}

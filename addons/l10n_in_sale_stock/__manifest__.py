# -*- coding: utf-8 -*-
{
    'name': "India Sales and Warehouse Management",

    'summary': """
        Define default sales journal on the warehouse""",

    'description': """
        Define default sales journal on the warehouse,
        help you to choose correct sales journal on the sales order when
        you change the picking operation.

        useful when you setup the multiple gstn units.
    """,

    'author': "Odoo",
    'website': "https://www.odoo.com",
    'category': 'Localization',
    'version': '0.1',

    'depends': ['l10n_in_sale', 'l10n_in_stock'],

    'data': [
        'views/stock_views.xml'
    ],
    'demo': [

    ],
    'auto_install': True
}

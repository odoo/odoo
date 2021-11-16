# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
   'name': 'FG Custom Addons',
    'version': '1.0',
    'category': 'FG/FG',
    'description': """
    Pilmico custom addons
        """,
    'depends': ['product', 'account', 'point_of_sale'],
    'data': [
        'views/FgOrderDetails.xml',
        'views/FgImportOrders.xml',
        'views/FgMessageWizard.xml',
        'views/FgPosOrder.xml',
        'security/ir.model.access.csv'
    ],
    'author': "1FG",
     'demo': [],
     'assets': {
        'point_of_sale.assets': [
            'fg_custom/static/src/pos/js/**/*',
            'fg_custom/static/src/pos/css/**/*',
        ],
        'web.assets_qweb': [
            'fg_custom/static/src/pos/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
     'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False
}

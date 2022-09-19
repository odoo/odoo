# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
   'name': 'FG Custom Addons',
    'version': '1.0',
    'category': 'FG/FG',
    'description': """
    Pilmico custom addons
        """,
    'depends': ['product', 'account', 'point_of_sale', 'base'],
    'data': [
        'views/FgOrderDetails.xml',
        'views/FgImportOrders.xml',
        'views/FgMessageWizard.xml',
        'views/FgCustomerMaster.xml',
        'views/FgPosOrder.xml',
        'views/FgPosSessionView.xml',
        'views/account_tax_views.xml',
        'views/point_of_sale_sequence.xml',
        'wizard/x_report_view.xml',
        'wizard/z_report_view.xml',
        'views/FgPosReport.xml',
        'views/x_report.xml',
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
        'web.assets_backend': [
            'fg_custom/static/src/base/*',
        ],
    },
    'license': 'LGPL-3',
     'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "pos_hr",
    'category': "Hidden",
    'summary': 'Link module between Point of Sale and HR',

    'description': """
This module allows Employees (and not users) to log in to the Point of Sale application using a barcode, a PIN number or both.
The actual till still requires one user but an unlimited number of employees can log on to that till and process sales.
    """,

    'depends': ['point_of_sale', 'hr'],

    'data': [
        'views/pos_config.xml',
        'views/pos_order_view.xml',
        'views/pos_order_report_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale.assets': [
            'pos_hr/static/src/css/pos.css',
            'pos_hr/static/src/js/models.js',
            'pos_hr/static/src/js/useSelectEmployee.js',
            'pos_hr/static/src/js/Chrome.js',
            'pos_hr/static/src/js/HeaderLockButton.js',
            'pos_hr/static/src/js/CashierName.js',
            'pos_hr/static/src/js/LoginScreen.js',
        ],
        'web.assets_tests': [
            'pos_hr/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'pos_hr/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}

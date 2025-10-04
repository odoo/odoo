# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "POS - HR",
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
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_hr/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_hr/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hr Expense Extract',
    'version': '1.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Extract data from expense scans to fill them automatically',
    'depends': ['hr_expense', 'iap_extract', 'iap_mail', 'mail_enterprise', 'hr_expense_predict_product'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/expense_sample_receipt_views.xml',
        'wizard/expense_sample_register_views.xml',
        'views/hr_expense_views.xml',
        'views/res_config_settings_views.xml',
        'data/crons.xml',
        ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'hr_expense_extract/static/src/**/*',
        ],
    }
}

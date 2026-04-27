# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Account Batch Payment Reconciliation',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Allows using Reconciliation with the Batch Payment feature.',
    'depends': ['account_accountant', 'account_batch_payment'],
    'data': [
        'security/ir.model.access.csv',

        'views/bank_rec_widget_views.xml',
        'views/account_batch_payment_rejection_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'account_accountant_batch_payment/static/src/components/**/*',
        ],
        'web.assets_tests': [
            'account_accountant_batch_payment/static/tests/tours/*.js',
        ],
    }
}

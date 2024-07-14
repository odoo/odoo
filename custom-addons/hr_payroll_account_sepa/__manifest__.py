# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "SEPA Payments for Payroll",
    'summary': "Pay your employees with SEPA payment.",
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': ['hr_payroll_account', 'account_sepa'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payroll_account_sepa_views.xml',
        'wizard/hr_payroll_account_sepa_wizard_views.xml',
        'views/hr_employee_views.xml'
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'hr_payroll_account_sepa/static/src/**/*.js',
            'hr_payroll_account_sepa/static/src/**/*.xml',
        ],
    },
}

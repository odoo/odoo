# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "SEPA Payments for Payroll",
    'summary': "Pay your employees with SEPA payment.",
    'category': 'Human Resources/Payroll',
    'version': '1.0',
    'depends': ['hr_payroll_account', 'account_iso20022'],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'data/hr_payroll_dashboard_warning_data.xml',
        'wizard/hr_payroll_payment_report_wizard.xml',
    ],
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'hr_payroll_account_iso20022/static/src/**/*.js',
            'hr_payroll_account_iso20022/static/src/**/*.scss',
            'hr_payroll_account_iso20022/static/src/**/*.xml',
        ],
    },
}

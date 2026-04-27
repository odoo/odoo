# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Expenses in Payslips',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'sequence': 95,
    'summary': 'Submit, validate and reinvoice employee expenses',
    'description': """
Reimbursement of expenses in Payslips
=====================================

This application allows you to reimburse expenses in payslips.
    """,
    'depends': ['hr_expense', 'hr_payroll_account'],
    'data': [
        'views/hr_expense_views.xml',
        'views/hr_payslip_views.xml',
        'data/hr_payroll_expense_data.xml',
        'wizard/account_payment_register_views.xml',
    ],
    'demo': ['data/hr_payroll_expense_demo.xml'],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}

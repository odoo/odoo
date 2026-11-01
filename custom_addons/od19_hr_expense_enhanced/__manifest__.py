# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Enhanced',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': (
        'Enhanced expense management: department head auto-approver, '
        'cash tracking, XLSX reports, WHT, and delegate approvals.'
    ),
    'author': 'OD19',
    'website': 'https://od19.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'account',
        'mail',
        'od19_accounting_features',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expense_views.xml',
        'views/account_payment_views.xml',
        'views/expense_xlsx_export_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

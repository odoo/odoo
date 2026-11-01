# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Enhanced',
    'version': '19.0.1.1.0',
    'category': 'Human Resources/Expenses',
    'summary': (
        'Enhanced expense management: department head auto-approver, '
        'cash tracking, XLSX reports, WHT, delegate approvals, and '
        'payment certificate in lieu of receipt (ใบรับรองแทนใบเสร็จรับเงิน).'
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
        'report/payment_certificate_report.xml',
        'views/hr_expense_views.xml',
        'views/account_payment_views.xml',
        'views/expense_xlsx_export_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    "icon": "/od19_hr_expense_enhanced/static/description/icon.svg",
}

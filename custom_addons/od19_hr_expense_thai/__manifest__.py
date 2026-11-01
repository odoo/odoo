# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Thai Localization',
    'author': 'OD19',
    'version': '19.0.1.1.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Thai HR expense extensions: cash reimbursement, multi-tier approval',
    'depends': [
        'hr_expense',
        'od19_hr_expense_enhanced',
        'od19_accounting_features',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expense_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    "icon": "/od19_hr_expense_thai/static/description/icon.svg",
}

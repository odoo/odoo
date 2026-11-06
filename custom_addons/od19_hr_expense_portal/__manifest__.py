# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Portal',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': (
        'Employee-facing expense experience: a quick submission wizard and a '
        '"My Expenses" kanban for HR Expense.'
    ),
    'author': 'OD19',
    'website': 'https://od19.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'od19_hr_expense_thai',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_expense_quick_create_views.xml',
        'views/hr_expense_kanban_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Thai Localization',
    'author': 'OD19',
    'version': '19.0.1.3.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Thai HR expense extensions: cash reimbursement, multi-tier approval',
    'depends': [
        'hr_expense',
        'hr_expense_tier_validation',
        'base_tier_validation',
        'base_tier_validation_forward',
        'od19_hr_expense_enhanced',
        'od19_accounting_features',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_expense_security.xml',
        'data/tier_definition_data.xml',
        'views/hr_expense_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    "icon": "/od19_hr_expense_thai/static/description/icon.svg",
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Project Expenses',
    'version': '1.0',
    'category': 'Services/expenses',
    'summary': 'Project expenses',
    'description': 'Bridge created to add the number of expenses linked to an AA to a project form',
    'depends': ['project_account', 'hr_expense'],
    'data': [
        'views/project_project_views.xml',
    ],
    'demo': [
        'data/project_hr_expense_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

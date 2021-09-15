# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Project Accounting',
    'version': '1.0',
    'category': 'Services/account',
    'summary': 'Project accounting',
    'description': 'Bridge created to remove the profitability setting if the account module is installed',
    'depends': ['project', 'account'],
    'data': [
        'views/project_project_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

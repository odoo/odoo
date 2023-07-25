# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Project Sales Accounting',
    'version': '1.0',
    'category': 'Services/account',
    'summary': 'Project sales accounting',
    'description': 'Bridge created to add the number of vendor bills linked to an AA to a project form',
    'depends': ['sale_timesheet', 'account'],
    'data': [
        'views/project_project_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

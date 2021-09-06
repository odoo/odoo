# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Account Sale Timesheet',
    'version': '1.0',
    'category': 'Account/sale/timesheet',
    'summary': 'Account sale timesheet',
    'description': 'Bridge created to add the number of invoices linked to an AA to a project form',
    'depends': ['account', 'sale_timesheet'],
    'data': [
        'views/project_project_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

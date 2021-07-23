# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Attendance Presence',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 85,
    'summary': 'Bridge Attendance module and Presence module',
    'description': "",
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['hr_attendance', 'hr_presence'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_employee.xml',
    ],
    'license': 'LGPL-3',
}

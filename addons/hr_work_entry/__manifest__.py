#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Work Entries',
    'category': 'Human Resources/Employees',
    'sequence': 39,
    'summary': 'Manage work entries',
    'description': "",
    'installable': True,
    'depends': [
        'hr',
    ],
    'data': [
        'security/hr_work_entry_security.xml',
        'security/ir.model.access.csv',
        'data/hr_work_entry_data.xml',
        'views/hr_work_entry_views.xml',
<<<<<<< HEAD
        'views/resource_views.xml',
=======
        'views/hr_employee_views.xml',
        'views/resource_calendar_views.xml',
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
    ],
    'qweb': [
        "static/src/xml/work_entry_templates.xml",
    ],
}

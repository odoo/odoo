# -*- coding: utf-8 -*-
{
    'name': 'Employee Directory',
    'version': '1.1',
    'author': 'Odoo S.A.',
    'category': 'Human Resources',
    'sequence': 21,
    'website': 'https://www.odoo.com/page/employees',
    'summary': 'Jobs, Departments, Employees Details',
    'description': """
Human Resources Management
==========================

This application enables you to manage important aspects of your company's staff and other details such as their skills, contacts, working time...


You can manage:
---------------
* Employees and hierarchies : You can define your employee with User and display hierarchies
* HR Departments
* HR Jobs
    """,
    'images': [
        'images/hr_department.jpeg',
        'images/hr_employee.jpeg',
        'images/hr_job_position.jpeg',
        'static/src/img/default_image.png',
    ],
    'depends': [
        'base_setup',
        'mail',
        'resource',
        'board',
        'web_kanban',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'views/hr_view.xml',
        'views/hr_installer.xml',
        'data/hr_data.xml',
        'data/hr_tip_data.xml',
        'views/res_config_view.xml',
        'views/mail_hr_view.xml',
        'views/res_users_view.xml',
        'views/hr.xml',
    ],
    'demo': ['data/hr_demo.xml'],
    'installable': True,
    'application': True,
    'qweb': ['static/src/xml/suggestions.xml'],
}

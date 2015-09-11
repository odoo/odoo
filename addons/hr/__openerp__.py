# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Directory',
    'version': '1.1',
    'category': 'Human Resources',
    'sequence': 75,
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
    'website': 'https://www.odoo.com/page/employees',
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
        'web_kanban',
        'web_tip',
    ],
    'data': [
        'security/hr_security.xml',
        'security/ir.model.access.csv',
        'hr_view.xml',
        'hr_installer.xml',
        'hr_data.xml',
        'hr_tip_data.xml',
        'res_config_view.xml',
        'views/hr.xml',
        'hr_dashboard.xml',
    ],
    'demo': ['hr_demo.xml'],
    'test': [
        'test/hr_users.yml',
        'test/open2recruit2close_job.yml',
        'test/hr_demo.yml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'qweb': [],
}

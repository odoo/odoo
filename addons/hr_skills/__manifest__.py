# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Management',
    'category': 'Human Resources/Employees',
    'sequence': 270,
    'version': '1.0',
    'summary': 'Manage skills, knowledge and resume of your employees',
    'description':
        """
Skills and Resume for HR
========================

This module introduces skills and resume management for employees.
        """,
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_skills_security.xml',
        'views/hr_views.xml',
        'views/hr_employee_skill_log_views.xml',
        'data/hr_resume_data.xml',
        'data/ir_actions_server_data.xml',
        'report/hr_employee_skill_report_views.xml',
        'views/hr_department_views.xml',
    ],
    'demo': [
        'data/hr_resume_demo.xml',
        'data/hr.employee.skill.csv',
        'data/hr.resume.line.csv',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'hr_skills/static/src/fields/skills_one2many.xml',
            'hr_skills/static/src/fields/*',
            'hr_skills/static/src/scss/*.scss',
            'hr_skills/static/src/views/*.js',
            'hr_skills/static/src/xml/**/*',
        ],
        'web.assets_tests': [
            'hr_skills/static/tests/tours/*',
        ],
    },
    'license': 'LGPL-3',
}

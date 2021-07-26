# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Management',
    'category': 'Human Resources/Employees',
    'sequence': 270,
    'version': '1.0',
    'summary': 'Manage skills, knowledge and resumé of your employees',
    'description':
        """
Skills and Resumé for HR
========================

This module introduces skills and resumé management for employees.
        """,
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_skills_security.xml',
        'views/hr_views.xml',
        'data/hr_resume_data.xml',
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
            'hr_skills/static/src/css/hr_skills.scss',
            'hr_skills/static/src/js/resume_widget.js',
        ],
        'web.qunit_suite_tests': [
            'hr_skills/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'hr_skills/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}

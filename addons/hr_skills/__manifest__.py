# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Skills',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Skills and Resumé for HR
========================

This module extend the employee with skills and resumé for employees.
        """,
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_skills_security.xml',
        'views/hr_views.xml',
        'views/hr_templates.xml',
        'data/hr_resume_data.xml',
    ],
    'demo': ['data/hr_resume_demo.xml'],
    'qweb': [
        'static/src/xml/resume_templates.xml',
        'static/src/xml/skills_templates.xml',
    ]
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Certification',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add certification to Resumes of your employees',
    'description':
        """
Certification and Skills for HR
===============================

This module adds certification to Resumes for employees.
        """,
    'depends': ['hr_skills', 'survey'],
    'data': [
        'views/hr_templates.xml',
        'data/hr_resume_data.xml',
    ],
    'qweb': [
        'static/src/xml/resume_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

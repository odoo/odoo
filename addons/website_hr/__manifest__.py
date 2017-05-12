# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Team Page',
    'category': 'Human Resources',
    'summary': 'Present Your Team',
    'description': """
Our Team Page
=============

        """,
    'depends': ['website', 'hr'],
    'demo': [
        'data/hr_employee_demo.xml',
    ],
    'data': [
        'security/hr_employee_security.xml',
        'security/ir.model.access.csv',
        'data/website_hr_data.xml',
        'views/website_hr_templates.xml',
        'views/hr_employee_views.xml',
    ],
}

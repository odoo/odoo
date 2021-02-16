# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'RFP',
    'version': '14.0.1.0.0',
    'summary': 'Relational Field Practice',
    'sequence': 10,
    'description': """
RFP & Details
====================

    """,
    'category': '',
    'website': 'https://www.xyz.com',
    'data': [
        'views/courses_views.xml',
        'views/subject_views.xml',
        'security/ir.model.access.csv',
        'views/student_views.xml',
        'views/department_views.xml',
        'views/faculty_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

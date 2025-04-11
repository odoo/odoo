# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Events',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Link training events to resume of your employees',
    'description':
        """
Events and Skills for HR
============================

This module add completed course events to resume for employees.
        """,
    'depends': ['hr_skills', 'event'],
    'data': [
        'views/hr_resume_line_views.xml',
        'views/event_event_views.xml',
        'views/hr_views.xml',
    ],
    'auto_install': True,
    'assets': {},
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

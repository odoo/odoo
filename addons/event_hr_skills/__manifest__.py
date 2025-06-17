{
    'name': 'Events HR Skills',
    'category': 'Marketing/Events',
    'summary': "Manage Employees' Events",
    'description': """
Link Employees to the events they attend, and display them on their resume.
""",
    'depends': ['hr_skills', 'event'],
    'data': [
        'views/event_category_tag_views.xml',
        'views/event_event_views.xml',
        'views/hr_resume_line_views.xml',
    ],
    'demo': [
        'data/event_hr_skills_demo.xml'
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'event_hr_skills/static/src/fields/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

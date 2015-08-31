{
    'name': 'Team Page',
    'category': 'Website',
    'summary': 'Present Your Team',
    'version': '1.0',
    'description': """
Our Team Page
=============

        """,
    'depends': ['website', 'hr'],
    'demo': [
        'data/hr_employee_demo.xml',
    ],
    'data': [
        'data/website_hr_data.xml',
        'views/website_hr_templates.xml',
        'views/hr_employee_views.xml',
        'security/ir.model.access.csv',
        'security/hr_employee_security.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

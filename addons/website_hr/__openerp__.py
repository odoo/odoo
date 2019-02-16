{
    'name': 'Team Page',
    'category': 'Human Resources',
    'summary': 'Present Your Team',
    'version': '1.0',
    'description': """
Our Team Page
=============

        """,
    'depends': ['website', 'hr'],
    'demo': [
        'data/website_hr_demo.xml',
    ],
    'data': [
        'data/website_hr_data.xml',
        'views/website_hr.xml',
        'views/website_hr_view.xml',
        'security/ir.model.access.csv',
        'security/website_hr.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

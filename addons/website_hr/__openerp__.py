{
    'name': 'Team Page',
    'category': 'Website',
    'summary': 'Present Your Team',
    'version': '1.0',
    'description': """
Our Team Page
=============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'hr'],
    'demo': [
        'data/website_hr_demo.xml',
    ],
    'data': [
        'data/website_hr_data.xml',
        'views/website_hr.xml',
        'security/ir.model.access.csv',
        'security/website_hr.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

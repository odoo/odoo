{
'name': 'Team Page',
    'category': 'Website',
    'summary': 'Present Your Team',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'hr'],
    'data': [
        'views/website_hr.xml',
        'security/ir.model.access.csv',
        'security/website_hr.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

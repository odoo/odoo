{
    'name': 'Career Form',
    'category': '',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'hr', 'hr_recruitment'],
    'data': [
        'views/website_hr_recruitment.xml'
    ],
    'css': ['static/lib/bootstrap/css/*.css'],
    'installable': True,
    'auto_install': False,
}

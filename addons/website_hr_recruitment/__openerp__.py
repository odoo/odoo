{
    'name': 'Career Form',
    'category': '',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'hr', 'hr_recruitment', 'website_mail'],
    'data': [
        'views/website_hr_recruitment.xml',
        'security/website_hr_recruitment_security.xml',
    ],
    'css':[
       'static/src/css/*.css'
      ],
    'installable': True,
    'auto_install': False,
}

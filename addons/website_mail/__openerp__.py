{
    'name': 'Blog',
    'category': 'mail',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'mail'],
    'data': [
        'views/website_mail.xml',
        'views/res_config.xml',
        'security/website_mail.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': True,
}

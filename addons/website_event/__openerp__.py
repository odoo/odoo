{
    'name': 'Website Event',
    'category': 'mail',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'event', 'website_sale'],
    'data': [
        'views/website_event.xml',
        'security/ir.model.access.csv',
        'security/website_event.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': True,
}

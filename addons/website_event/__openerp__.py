{
    'name': 'Online Events',
    'category': 'Website',
    'summary': 'Schedule, Promote and Sell Events',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'event_sale', 'website_sale'],
    'data': [
        'views/website_event.xml',
        'security/ir.model.access.csv',
        'security/website_event.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

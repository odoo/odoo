{
'name': 'Public References',
    'category': 'Website',
    'summary': 'Publish Customer References',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'sale'],
    'data': [
        'views/website_contract.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

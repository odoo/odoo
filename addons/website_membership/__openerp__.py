{
    'name': 'Public Partners Members',
    'category': 'Website',
    'summary': 'Publish Members',
    'version': '1.0',
    'description': """
OpenERP Partners Members
========================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_partner', 'association'],
    'data': [
        'views/website_membership.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

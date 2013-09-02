{
'name': 'Public Partners References',
    'category': 'Website',
    'summary': 'Publish Customer References',
    'version': '1.0',
    'description': """
OpenERP Public Partners References
==================================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'website_google_map'],
    'data': [
        'views/website_crm_partner_assign.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

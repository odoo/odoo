{
    'name': 'Public Members',
    'name': 'Website for Associations',
    'category': 'Website',
    'summary': 'Publish Associations, Groups and Memberships',
    'version': '1.0',
    'description': """
Website for browsing Associations, Groups and Memberships
=========================================================
""",
    'author': 'OpenERP SA',
    'depends': ['website_partner', 'website_google_map', 'association'],
    'data': ['views/website_membership.xml',],
    'demo': ['demo/membership.xml'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

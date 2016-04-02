{
    'name': 'Associations: Members',
    'summary': 'Online Directory of Members',
    'category': 'Website',
    'summary': 'Publish Associations, Groups and Memberships',
    'version': '1.0',
    'description': """
Website for browsing Associations, Groups and Memberships
=========================================================
""",
    'depends': ['website_partner', 'website_google_map', 'association', 'website_sale'],
    'data': [
        'views/website_membership.xml',
        'security/ir.model.access.csv',
        'security/website_membership.xml',
    ],
    'demo': ['demo/membership.xml'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

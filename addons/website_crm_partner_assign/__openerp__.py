{
    'name': 'Publish Partner Assignment',
    'category': 'Website',
    'summary': 'Publish and Assign Partner',
    'version': '1.0',
    'description': """
Publish and Assign Partner
==========================
        """,
    'author': 'OpenERP SA',
    'depends': ['crm_partner_assign','website_partner', 'website_google_map'],
    'data': [
        'views/website_crm_partner_assign.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

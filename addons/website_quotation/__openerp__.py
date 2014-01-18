{
    'name': 'Online Quotation',
    'category': 'Website',
    'summary': 'Send Live Quotation',
    'version': '1.0',
    'description': """
OpenERP Sale Quote Roller
==================

        """,
    'author': 'OpenERP SA',
    'depends': ['website','sale', 'portal_sale', 'mail','document'],
    'data': [
        'views/website_quotation.xml',
        'views/website_quotation_backend.xml',
        'data/website_quotation_data.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/website_quotation_demo.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

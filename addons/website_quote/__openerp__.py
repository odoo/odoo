{
    'name': 'Online Proposals',
    'category': 'Website',
    'summary': 'Send Professional Quotations',
    'version': '1.0',
    'description': """
OpenERP Sale Quote Roller
=========================

        """,
    'author': 'OpenERP SA',
    'depends': ['website','sale', 'mail'],
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

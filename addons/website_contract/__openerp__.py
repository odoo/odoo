{
    'name': 'Website Contract',
    'category': 'Website',
    'summary': 'Contract Management Frontend for your Clients',
    'version': '1.0',
    'description': """
Allows your customers to manage their contract from a beautiful web interface. Automatic payments included!
        """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/',
    'depends': [
        'sale_contract',
        'website_sale',
        'website_portal',
        'website_quote',
        'website_payment'
    ],
    'data': [
        'views/templates.xml',
        'views/views.xml',
        'security/ir.model.access.csv',
        'security/portal_contract_security.xml',
        'data/data.xml'
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'application': True,
}

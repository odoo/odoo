{
    'name': 'Website Portal',
    'category': 'Website',
    'summary': 'Account Management Frontend for your Customers',
    'version': '1.0',
    'description': """
Allows your customers to manage their account from a beautiful web interface.
        """,
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/',
    'depends': [
        'sale',
        'website',
    ],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
    ],
    'demo': [
        'data/demo.xml'
    ],
    'installable': True,
}

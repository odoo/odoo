{
    'name': 'Contact Form',
    'category': 'Website',
    'summary': 'Generate Leads From Contact Form',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'crm'],
    'data': [
        'views/website_crm.xml'
    ],
    'js': ['static/src/js/ecommerce.js'],
    'css': ['static/src/css/ecommerce.css'],
    'installable': True,
}

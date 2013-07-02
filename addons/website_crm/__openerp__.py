{
    'name': 'Contact Form',
    'category': 'CRM',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'crm'],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/website_crm.xml'
    ],
    'js': ['static/src/js/ecommerce.js'],
    'css': ['static/src/css/ecommerce.css'],
}

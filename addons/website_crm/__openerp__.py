{
    'name': 'Website Contact Form',
    'category': 'Website',
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
    'auto_install': True,
}

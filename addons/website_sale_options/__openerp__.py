{
    'name': 'eCommerce Optional Products',
    'category': 'Website',
    'version': '1.0',
    'website': 'https://www.odoo.com/page/e-commerce',
    'description': """
Odoo E-Commerce
==================

        """,
    'depends': ['website_sale'],
    'data': [
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
}

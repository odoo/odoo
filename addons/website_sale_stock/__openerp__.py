# -*- encoding: utf-8 -*-
{
    'name': 'Website Sale Stock - Website Delivery Informations',
    'version': '0.0.1',
    'description': """
    Display delivery orders (picking) infos on the website
""",
    'author': 'Odoo S.A.',
    'depends': [
        'website_sale',
        'sale_stock',
    ],
    'installable': True,
    'auto_install': True,
    'data': [
        'views/website_sale_stock.xml',
    ],
    'demo': [
    ],
}

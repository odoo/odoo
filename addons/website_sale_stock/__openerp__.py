# -*- encoding: utf-8 -*-
{
    'name': 'Website Sale Stock - Website Delivery Informations',
    'version': '0.0.1',
    'category': 'Website',
    'description': """
    Display delivery orders (picking) infos on the website
""",
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

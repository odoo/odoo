# -*- coding: utf-8 -*-
{
    'name': "Three Images Per Website Product",

    'summary': """
        Add two more images per website product with zoom lens feature """,

    'description': """
        This Module will make it possible to add and display 2 more images for the website product
    """,
    'images': ['static/description/photo.png'],
    'author': "Optima ICT Services LTD",
    'website': "http://optima.co.ke",
    'price': 9,
    'currency': 'EUR',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/templates.xml',
	'views/product_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

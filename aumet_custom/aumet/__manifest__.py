# -*- coding: utf-8 -*-
{
    'name': "Aumet",

    'summary': """
                Marketplace Integration""",

    'description': """
        Aumet marketplace integration 
        - Authentication
        - Sync Products
        - Sync distributors
        - add products to car
    """,

    'author': "Ahmad Da'na",
    'website': "http://www.aumet.com",
    'category': 'Apps',
    'version': '0.1',

    'depends': ['base', 'product', 'base_setup', 'point_of_sale', 'purchase'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/res_company_views.xml',
        'views/assets.xml'
    ],

    'images': ['static/description/icon.png'],

    'qweb': [
        'views/templates.xml'
    ],

    'installable': True,
    'application': True
}

# -*- coding: utf-8 -*-
{
    'name': "Socioll Addons",
    'summary': """
        Addon featured for PT. Social Bella Indonesia""",

    'description': """
        Version 1:
            - Add posting journal Sales Discount
            - Add posting journal Sales Return
            - Add brand for product
    """,

    'author': "Internal Development - PT. Social Bella Indonesia",
    'website': "http://www.sociolla.com",
    'category': 'Addon Sociolla',
    'version': '1',
    'installable': True,
    'application': True,

    'depends': ['base', 'account', 'product', 'sale'],

    'data': [
        'views/product_view.xml',
        'views/product_brand_view.xml',

        'security/ir.model.access.csv',
    ],
}
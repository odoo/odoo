# -*- coding: utf-8 -*-
{
    'name': "Sociolla Addons",
    'summary': """
        Addon feature for PT. Social Bella Indonesia""",

    'description': """
        Version 0.1:
            - Add posting journal Sales Discount
            - Add posting journal Sales Return
        
        Version 0.2:
            - Add Connector Odoo - Prestashop 
    """,

    'author': "Internal Development - PT. Social Bella Indonesia",
    'website': "http://www.sociolla.com",
    'category': 'Addon Sociolla',
    'version': '0.2 beta',
    'installable': True,
    'application': True,

    'depends': [
        'base', 
        'account', 
        'product', 
        'sale', 
        'product_brand',
    ],

    'data': [
        'views/product_view.xml',

    ],
}
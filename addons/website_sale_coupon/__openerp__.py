# -*- coding: utf-8 -*-
{
    'name': "website_sale_coupon",
    'summary': """Allows to use discount coupons in sales order and in ecommerce""",
    'description': """Allows to use discount coupons in sales order and in ecommerce """,
    'author': "OpenERP SA",
    'website': "http://www.odoo.com",
    'category': 'Coupons',
    'version': '0.1',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/SaleCoupon.xml',
        'views/templates.xml',
        'data/data.xml',
    ],
    'demo': [
        #'demo.xml',
    ],
}

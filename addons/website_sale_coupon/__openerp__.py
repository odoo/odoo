# -*- coding: utf-8 -*-
{
    'name': "website_sale_coupon",

    'summary': """Allows to use discount coupons in sales order and in ecommerce""",

    'description': """Allows to use discount coupons in sales order and in ecommerce """,

    'author': "OpenERP SA",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['website_sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/SaleCoupon.xml',
        #'views/templates.xml',
        'data/data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo.xml',
    ],
}
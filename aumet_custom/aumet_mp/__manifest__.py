# -*- coding: utf-8 -*-
{
    'name': "Aumet Market Place",

    'summary': """
             Aumet Market Place Integration module.
        """,

    'description': """
         Aumet Market Place Integration module.
        - Authentication
        - Sync Products
        - Sync Distributors
        - Add Products to cart  
    """,

    'author': "Mahmoud Al Shaikh",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'purchase', 'point_of_sale', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/marketplace_product_views.xml',
        'views/aumet_marketplace_views.xml',
        'views/product_views.xml',
        'views/purchase_views.xml',
        'data/ir_cron_data.xml',
        'views/assets.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],


    'installable': True,
    'application': True


}

# -*- coding: utf-8 -*-
{
    'name': "order_inheritance",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'version': '0.1',
    'sequence': 1,
    # any module necessary for this one to work correctly
    'depends': ['base', 'sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/product_type_view.xml',
        # 'views/supplier_view.xml',

        'views/views.xml',
        'views/templates.xml',
        'views/customer_view.xml',
        'views/product_view.xml',
        'views/order_view.xml',
        'views/sale_menu.xml',
        'views/stock_view.xml',

    ],
    # only loaded in demonstration mode
    "category": "Order inheritance/order_inheritance",
    'demo': [
        'demo/demo.xml',
    ],
    "application": True,
    "installable": True,
}

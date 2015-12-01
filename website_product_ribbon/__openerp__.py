# -*- coding: utf-8 -*-
{
    'name': "Product Promo Ribbons & Badges",

    'summary': """
        Tag your website products with appropriate promotional ribbons of any color, size or shape of your choice""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'website',
    'version': '0.1',
    'price': 29,
    'currency': 'EUR',
    'images': ['static/description/ribbon.png'],

    # any module necessary for this one to work correctly
    'depends': ['base', 'website_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/product_templates.xml',
        'views/data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'views/demo.xml',
    ],
}

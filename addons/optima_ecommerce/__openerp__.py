# -*- coding: utf-8 -*-
{
    'name': "Optima Ecommerce",

    'summary': """
        This Module will customize Odoo ecommerce application""",

    'description': """
        Optima Ecommerce Module was written to add necessary customizatiosn to the existing e-commerce application in order to suite our customer needs
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

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
        'views/optima.xml',
        'views/optima_website.xml',
        'views/data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

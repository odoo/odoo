# -*- coding: utf-8 -*-
{
    'name': "Jquery Validation plugin for Ecommerce",

    'summary': """
        A plugin that works together with our "Ecommerce Data Validation module" to validate billing & shipping information entered by user.
        """,

    'description': """
        This is a plugin to install jquery.validate.min.js and additional methods used to validate input data  enter by user in the ecommerce website
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",
    'images': ['static/description/icon.png'],
    'price': 5,
    'currency': 'EUR',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/jquery_validation.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

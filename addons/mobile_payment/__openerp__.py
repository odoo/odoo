# -*- coding: utf-8 -*-
{
    'name': "Mobile Money Payment",

    'summary': """
        This Module will integrate Mobile Money Payment option to any E-commerce Website that is powered by Odoo""",

    'description': """
        Customers will be able to choose Mobile Money payment(MPESA, Airtel Money etc) as one of the payment options on an Odoo powered e-commerce website
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],

    # always loaded
    'data': [
       # 'security/ir.model.access.csv',
        'views/mobile_money.xml',
        'views/mobile_money_config.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

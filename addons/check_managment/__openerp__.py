# -*- coding: utf-8 -*-
{
    'name': "check_managment",

    'summary': """
        Utravel check managment """,

    'description': """
        Utravel check managment
    """,

    'author': "Utravel",
    'website': "http://www.utravel.ae", 

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
          'data/account_payment_method_data.xml',
         'views/check_operation.xml' ,
        'views/check.xml' ,
        'views/account_journal_view.xml',
        'views/account_payment_view.xml',
        'views/check_transaction.xml',
        'views/conf.xml'

        
    ],
    # only loaded in demonstration mode TEST sHABIR
    'demo': [
        'demo/demo.xml'
    ],
}
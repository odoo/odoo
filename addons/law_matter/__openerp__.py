# -*- coding: utf-8 -*-
{
    'name': "Law Firm Management",

    'summary': """
        Law Firm Management Software""",

    'description': """
        Used to manage Clients, Matters, Client Trust Fund, Billable Activities, Expenses, Invoicing, Payments in a law firm etc
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'calendar'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'law.xml',
        'data.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

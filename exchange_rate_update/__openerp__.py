# -*- coding: utf-8 -*-
{
    'name': "Accounting: Exchange Rate Automatic Update",

    'summary': """
        Update your exchange rates automatically at intervals of your choice. Choose rates source between YAHOO and Oanda.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting & Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account'],
    'currency': 'EUR',
    'price': 19,
    'images': ['static/description/forex.png'],
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/company_view.xml',
        'views/cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'views/demo.xml',
    ],
}

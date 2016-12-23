# -*- coding: utf-8 -*-
{
    'name': "Professional Invoice Report",

    'summary': """
        Odoo Invoice Report customized to look elegant, professional and appealing, social media IDs added""",

    'description': """
        This module will install a customized client invoice report for accounting module.
    """,
    'images': ['static/description/inv.png'],
    'price': 19,
    'currency': 'EUR',


    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Accounting & Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'optima_social'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'reports/account_invoice.xml',
        'reports/reports.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

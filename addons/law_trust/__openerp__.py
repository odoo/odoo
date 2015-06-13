# -*- coding: utf-8 -*-
{
    'name': "Law Trust Fund Management",

    'summary': """
        Managment of Client Trust Account Operations in Law Firm""",

    'description': """
        A Module that introduces Client Trust Account Operation and managment. Links the Law Firm managment module with the Odoo accounting Module to enable the managmentof Client Trust Funds bt lawyers. Features include Trust deposit, Transfer, Disbursement and payment of legal fees, expenses or Tasks using trust fund
    """,

    'author': "Optima ICT services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'law_matter', 'account', 'account_voucher'],

    # always loaded
    'data': [
         'security/ir.model.access.csv',
        'law_trust.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

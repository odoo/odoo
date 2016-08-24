# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Accounting and Finance',
    'version': '1.1',
    'category': 'Accounting',
    'sequence': 35,
    'summary': 'Financial and Analytic Accounting',
    'description': """
Accounting Access Rights
========================
It gives the Administrator user access to all accounting features such as journal items and the chart of accounts.

It assigns manager and user access rights to the Administrator for the accounting application and only user rights to the Demo user.
""",
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account'],
    'data': [
        'security/account_security.xml',
        'account_accountant_data.xml'
    ],
    'demo': ['account_accountant_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}

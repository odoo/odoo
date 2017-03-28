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
    'depends': ['account', 'web_tour'],
    'data': [
        'data/account_accountant_data.xml',
        'data/account_accountant_tour.xml',
        'security/account_accountant_security.xml',
        'views/account_accountant_templates.xml',
        'views/res_config_view.xml',
        'views/product_views.xml',
    ],
    'demo': ['data/account_accountant_demo.xml'],
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}

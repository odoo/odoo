# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Payments Withholdings',
    'version': "1.0",
    'description': """
Functional
----------


Technical
---------
""",
    'author': 'ADHOC SA',
    'category': 'Invoices & Payments',
    'depends': [
        'account',
        'l10n_ar',  # ONLY FOR CHART TEMPLATE
    ],
    'data': [
        'views/account_tax_views.xml',
        'views/account_payment_view.xml',
        'wizards/account_payment_register_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_l10n_ar_withholding_post_init',
    'license': 'LGPL-3',
}

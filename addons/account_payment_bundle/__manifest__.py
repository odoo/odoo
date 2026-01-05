# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Payment Bundle',
    'version': "1.0",
    'description': """Allows to register related payment.""",
    'author': 'ADHOC SA',
    'category': 'Accounting/Accounting',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_payment_method_data.xml',
        'views/account_payment_views.xml',
        'wizard/account_payment_register_views.xml',
    ],
    'installable': True,
    'post_init_hook': '_payment_bundle_post_init',
    'license': 'LGPL-3',
}

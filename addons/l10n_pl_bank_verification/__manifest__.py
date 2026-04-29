# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Poland - Accounting - Bank Account Verification',
    'description': """
This is the module to manage the accounting bank account verification for Poland in Odoo.
==========================================================================================

This module checks the VAT/Bank account number combination for PL to PL payments over
15.000 PLN, against the government API

This module is added in stable version from 18.0 and the features inside it will be merged
in l10n_pl in 19.4
    """,
    'depends': [
        'l10n_pl',
    ],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/account_payment_view.xml',
        'wizard/account_payment_register_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

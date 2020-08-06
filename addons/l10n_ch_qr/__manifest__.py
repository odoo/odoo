# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Switzerland - QR-IBAN",
    'description': """
Swiss localization
==================
Added QR-IBAN on bank account.

If the bank account number is a valid QR-IBAN number, swiss code URL will be build using the same account number.
Otherwise, bank account number is IBAN number but not a valid QR-IBAN and QR-IBAN field holds a valid QR-IBAN number, swiss code URL will be build using new QR-IBAN field.
    """,
    'version': '1.0',
    'author': 'Odoo S.A',
    'category': 'Accounting/Localizations',
    'depends': ['l10n_ch'],
    'data': [
        'views/res_bank_views.xml',
    ],
    'auto-install': True,
}

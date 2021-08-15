# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Switzerland - QR-IBAN",
    'description': """
Swiss localization
==================
Added a QR-IBAN field on bank account.
If this field is empty but the bank account number itself is a valid QR-IBAN number, it will continue using it as QR-IBAN.
However, if the new QR-IBAN field is filled, the value will be used as the QR-IBAN.
This should help for reconciliation on the bank statements where the old IBAN code is still used.
    """,
    'version': '1.0',
    'author': 'Odoo S.A',
    'category': 'Localization',
    'depends': ['l10n_ch'],
    'data': [
        'views/res_bank_views.xml',
        'views/swissqr_report.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

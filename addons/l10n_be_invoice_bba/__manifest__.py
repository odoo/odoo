# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

{
    'name': 'Belgium - Structured Communication',
    'version': '1.2',
    'author': 'Noviat',
    'category': 'Accounting/Accounting',
    'description': """

Add Structured Communication to customer invoices.
--------------------------------------------------

Using BBA structured communication simplifies the reconciliation between invoices and payments.
You can select the structured communication as payment communication in Invoicing/Accounting settings.
Two algorithms are suggested:

    1) Invoice Number +++RRR/RRRR/RRRDD+++
        **R..R =** Invoice Number, **DD =** Check Digits
    2) Customer Reference +++RRR/RRRR/SSSDD+++
        **R..R =** Customer Reference without non-numeric characters, **SSS =** Sequence Number, **DD =** Check Digits
    """,
    'depends': ['account', 'l10n_be'],
    'data': [
        'data/mail_template_data.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - E-invoicing (Withholding)',
    'countries': ['it'],
    'version': '0.1',
    'depends': [
        'l10n_it_edi'
    ],
    'author': 'Odoo',
    'description': """
Withholding and Pension Fund handling for the E-invoice implementation for Italy.

    The Withholding tax and the Pension Fund tax are computed like every other tax
    with the ordering by sequence, so please be careful with the order of the taxes
    in your tax configuration.

    Please also update the Italian Accounting module (l10n_it) when you install this module.
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/16.0/applications/finance/accounting/fiscal_localizations/localizations/italy.html',
    'data': [
        'data/account_withholding_report_data.xml',
        'data/invoice_it_template.xml',
        'views/l10n_it_view.xml'
    ],
    'post_init_hook': '_l10n_it_edi_withholding_post_init',
    'license': 'LGPL-3',
}

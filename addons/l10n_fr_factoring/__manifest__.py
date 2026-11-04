# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'France - Factoring Payee',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Export a factoring IBAN as PayeeParty',
    'description': """
French factoring (DGFiP case 8)
===============================

When the company bank account selected on an invoice is flagged as factoring,
the e-invoice export emits BG-10 PayeeParty / PayeeTradeParty, document type
393 (invoice) or 396 (credit note) and payee role DL.

The factor is the holder of that bank account. This is not a third party
who pays the invoice instead of the customer.
    """,
    'depends': ['account_edi_ubl_cii', 'l10n_fr'],
    'auto_install': ['account_edi_ubl_cii', 'l10n_fr'],
    'data': [
        'views/res_partner_bank_views.xml',
    ],
    'license': 'LGPL-3',
}

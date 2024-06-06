# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - E-invoicing (PA)',
    'version': '0.1',
    'depends': [
        'l10n_it_edi'
    ],
    'auto_install': ['l10n_it_edi'],
    'author': 'Odoo',
    'description': """
Public Administration partners flow handling for the E-invoice implementation for Italy.

    Several more fields are required for invoicing Public Administration businesses.
    The Origin Document is to be exported in the XML when invoicing the Public Administration,
    It can be a Contract, an Agreement, a Purchase Order, a Linked Invoice or a Down Payment,
    it will need the CIG and CUP fields which are mandatory.
    They both serve the purpose to trace public funds being invested on purchases.
    CIG is the Tender Unique Identifier, CUP identifies the Public Project of Investment.
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/16.0/applications/finance/accounting/fiscal_localizations/localizations/italy.html',
    'data': [
        'views/account_move_view.xml',
        'views/report_invoice.xml',
    ],
    'license': 'LGPL-3',
}

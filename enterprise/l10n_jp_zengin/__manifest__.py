# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Japan - Zengin Payment",
    'description': """
This module enables the generation of Zengin-compliant files to send to your bank in order to
push a set of payments.
    """,
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'depends': ['l10n_jp', 'account_batch_payment', 'account_bank_statement_import'],
    'data': [
        'data/account_payment_method_data.xml',
        'views/account_batch_payment_views.xml',
        'views/account_journal_views.xml',
        'views/res_bank_views.xml',
        'views/res_partner_bank_views.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}

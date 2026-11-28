# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Thailand - e-Tax Invoice",
    'icon': '/account/static/description/l10n.png',
    'countries': ['th'],
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/thailand.html',
    'depends': [
        'account_debit_note',
        'l10n_th',
    ],
    'summary': "e-Tax Invoice using INET",
    'description': """
Thailand - e-Tax Invoice
========================
Sign e-Tax documents and submit them to the Revenue Department through INET.
    """,
    'data': [
        'data/ir_cron.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_debit_note_views.xml',
        'wizard/account_move_reversal_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

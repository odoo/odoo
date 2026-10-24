# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - QRPH with Maya',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'summary': "Pay invoices with a QRPH code minted by Maya.",
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'depends': [
        'l10n_ph',
    ],
    'data': [
        'security/ir.access.csv',
        'data/ir_cron_data.xml',
        'views/account_move_views.xml',
        'views/l10n_ph_qrph_transaction_views.xml',
        'views/res_bank_views.xml',
    ],
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia - Point of Sale',
    'description': """Indonesian Point of Sale""",
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_id',
        'pos_payment_method_bank_qr',
        'point_of_sale'
    ],
    'auto_install': True,
    'assets': {
        'point_of_sale.payment_terminals': [
            'l10n_id_pos/static/src/payment_method_bank_qr_qris.js'
        ],
        'web.assets_tests': [
            'l10n_id_pos/static/tests/**/*'
        ]
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

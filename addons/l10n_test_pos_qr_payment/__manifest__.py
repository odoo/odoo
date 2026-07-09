# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS QR Tests',
    'category': 'Sales/Point of Sale',
    'sequence': 9876,
    'description': """
        This module contains tests related to point of sale QR code payment.
        It tests all the supported qr codes: SEPA, Swiss QR and EMV QR (using the hk and br implementation)
    """,
    'depends': [
        'account_qr_code_sepa',
        'l10n_hk',
        'l10n_br',
        'l10n_be_pos',
        'l10n_ch_pos',
    ],
    'assets': {
        'web.assets_tests': [
            'l10n_test_pos_qr_payment/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

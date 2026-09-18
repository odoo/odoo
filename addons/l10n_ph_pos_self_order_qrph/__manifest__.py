# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - POS Self Order QRPH',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'category': 'Accounting/Localizations/Point of Sale',
    'summary': "Pay a kiosk order with a QRPH code minted by Maya.",
    'author': 'Odoo S.A.',
    'depends': [
        'l10n_ph_pos',
        'pos_self_order',
    ],
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'point_of_sale/static/lib/qrcode.js',
            'l10n_ph_pos_self_order_qrph/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}

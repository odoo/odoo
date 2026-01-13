# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Indonesia - POS Self Order',
    'description': """Indonesian POS Self Order""",
    'category': 'Accounting/Localizations/Point of Sale',
    "depends": [
        "l10n_id_pos",
        "pos_self_order"
    ],
    "auto_install": True,
    'assets': {
        'pos_self_order.assets': [
            "l10n_id_pos_self_order/static/src/app/pages/payment_page/payment_page.js",
            "l10n_id_pos_self_order/static/src/app/services/self_order.js",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}

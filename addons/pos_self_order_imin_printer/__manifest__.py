# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "POS Self Order iMin Printer",
    "summary": "Addon for the Self Order App that allows printing via iMin Printer.",
    "category": "Sales/Point Of Sale",
    "depends": ["pos_imin", "pos_self_order"],
    'assets': {
        'pos_self_order.assets': [
            'pos_imin/static/lib/imin-printer/imin-printer.js',
            'pos_imin/static/src/app/utils/imin_printer.js',
            'pos_self_order_imin_printer/static/src/app/**/*',
        ],
    },
    "auto_install": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}

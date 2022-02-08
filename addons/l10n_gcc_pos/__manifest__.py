# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gulf Cooperation Council - Point of Sale',
    'author': 'Odoo S.A',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
GCC POS Localization
=======================================================
    """,
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'l10n_gcc_invoice'],
    'data': [
    ],
    'assets': {
        'web.assets_qweb': [
            'l10n_gcc_pos/static/src/xml/OrderReceipt.xml',
        ],
        'point_of_sale.assets': [
            'l10n_gcc_pos/static/src/js/OrderReceipt.js',
            'l10n_gcc_pos/static/src/css/OrderReceipt.css',
        ]
    },
    'auto_install': True,
}

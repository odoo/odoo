# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Point of Sale',
    'author': 'Odoo S.A',
    'category': 'Accounting/Localizations/Point of Sale',
    'description': """
K.S.A. POS Localization
=======================================================
    """,
    'license': 'LGPL-3',
    'depends': [
        'l10n_gcc_pos',
        'l10n_sa',
    ],
    'assets': {
        'point_of_sale.assets': [
            'web/static/lib/zxing-library/zxing-library.js',
            'l10n_sa_pos/static/src/js/models.js',
            'l10n_sa_pos/static/src/xml/OrderReceipt.xml',
        ]
    },
    'auto_install': True,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Stock',
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_din5008',
        'stock',
    ],
    'data': [
        'report/din5008_stock_templates.xml',
        'report/din5008_stock_picking_layout.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_din5008_stock/static/src/scss/report_din5008.scss',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

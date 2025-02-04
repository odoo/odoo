# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Spain - Point of Sale + TicketBAI",
    'version': '1.0',
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_es_edi_tbai',
        'point_of_sale',
    ],
    'data': [
        'views/pos_order_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_es_edi_tbai_pos/static/src/**/*',
        ],
    },
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

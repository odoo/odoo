# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Spain - Stock - DeCA",
    'version': '1.1',
    'category': 'Accounting/Localizations',
    'description': """
This module lets the user generate the DeCA
(Documento electrónico de Control Administrativo) from deliveries.
    """,
    'depends': [
        'l10n_es',
        'stock',
    ],
    'data': [
        "security/ir.model.access.csv",
        "wizard/l10n_es_deca_wizard_views.xml",
        "views/stock_picking_views.xml",
        "report/report_picking_deca.xml",
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_es_stock/static/src/css/report_picking_deca.scss',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

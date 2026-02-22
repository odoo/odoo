# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portugal - Stock',
    'description': """Stock module for Portugal which allows hash and QR code on stock pickings""",
    'category': 'Accounting/Localizations/Stock',
    'depends': [
        'l10n_pt_certification',
        'stock',
    ],
    'data': [
        'data/ir_cron.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'views/res_config_settings_views.xml',
        'report/l10n_pt_stock_hash_integrity_templates.xml',
        'report/report_deliveryslip.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Kenya ETIMS EDI Stock Integration",
    'countries': ['ke'],
    'summary': """
            Kenya eTIMS Device EDI Stock Integration
        """,
    'description': """
       This module integrates with the Kenyan eTIMS device. (OSCU)
    """,
    'author': 'Odoo',
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'license': 'OEEL-1',
    'depends': ['l10n_ke_edi_oscu', 'sale_management', 'purchase_stock', 'sale_stock'],
    'data': [
        'data/ir_cron_data.xml',
        'data/ir_config_parameter.xml',
        'views/product_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'views/l10n_ke_edi_customs_import_views.xml',
        'views/account_move_views.xml',
        'views/purchase_views.xml',
        'security/ir.model.access.csv',
        'security/l10n_ke_security.xml',
    ],
    'auto_install': True,
}

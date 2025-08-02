# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'author': 'Odoo',
    'name': 'Romania - Send E-Factura',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': "Bridge module for sending Romanian E-Factura to the SPV",
    'countries': ['ro'],
    'depends': ['l10n_ro_edi'],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_move_send_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

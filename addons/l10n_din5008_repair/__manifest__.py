# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Repair',
    'category': 'Accounting/Localizations',
    'depends': [
        'repair',
        'l10n_din5008_sale',
        'l10n_din5008_stock',
    ],
    'data': [
        'report/din5008_repair_templates.xml',
        'report/din5008_repair_order_layout.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

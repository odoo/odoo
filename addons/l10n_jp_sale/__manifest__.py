# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Japan - Sale',
    'countries': ['jp'],
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'depends': [
        'l10n_jp',
        'sale',
    ],
    'data': [
        'security/ir.access.csv',
        'data/l10n_jp_closing_day_data.xml',
        'report/ir_actions_report_templates.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

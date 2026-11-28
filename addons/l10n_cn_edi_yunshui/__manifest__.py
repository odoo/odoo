# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'China - E-Fapiao (Aisino Yunshui)',
    'countries': ['cn'],
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    'summary': "Issue e-Fapiao through Aisino Yunshui 爱信诺云税",
    'description': """
Issue fully-digital e-Fapiao (数电发票) from Odoo invoices through Aisino Yunshui (爱信诺云税),
reverse them with red fapiao, and handle the red letter confirmation forms (红字确认单)
the other party raises.

Each company uses its own organization code (组织编码) and identity code (授权码).
    """,
    'depends': ['l10n_cn', 'phone_validation'],
    'data': [
        'security/ir.access.csv',
        'data/ir_cron.xml',
        'data/l10n_cn_edi.tax.category.csv',
        'views/account_move_views.xml',
        'views/account_move_reversal_views.xml',
        'views/account_tax_views.xml',
        'views/l10n_cn_edi_document_views.xml',
        'views/product_template_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/l10n_cn_edi_yunshui_login_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

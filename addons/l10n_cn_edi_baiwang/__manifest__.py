# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'China - E-invoicing',
    'countries': ['cn'],
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    "summary": "E-invoicing using MyInvois",
    'description': """
    This modules allows the user to send their invoices to the MyInvois system.
    """,
    'depends': ['l10n_cn'],
    'auto_install': ['l10n_cn'],
    'data': [
        'data/ir_cron.xml',

        'security/ir.model.access.csv',

        'views/account_move_view.xml',
        'views/product_template_view.xml',
        'views/res_config_settings_view.xml',

        # 'wizard/cninvois_consolidate_invoice_wizard.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

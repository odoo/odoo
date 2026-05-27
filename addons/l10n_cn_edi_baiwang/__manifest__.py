# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'China - E-invoicing (Baiwang)',
    'countries': ['cn'],
    'category': 'Accounting/Localizations/EDI',
    'icon': '/account/static/description/l10n.png',
    'summary': "E-Fapiao integration via Baiwang (百望)",
    'description': """
Chinese e-Fapiao (电子发票) integration through the Baiwang Open API platform.

Features:
- Issue fully-digital e-Fapiao (全电发票) directly from Odoo invoices
- Automatic red letter confirmation form workflow for credit notes
- Integration with Send & Print wizard
- Periodic status polling for pending red form confirmations
- Support for both digital (01/02) and tax-controlled (004/007/026/028) invoice types
    """,
    'depends': ['l10n_cn', 'account'],
    'auto_install': ['l10n_cn'],
    'data': [
        'data/ir_cron.xml',

        'security/ir.model.access.csv',

        'views/account_move_view.xml',
        'views/account_move_reversal_view.xml',
        'views/product_template_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'author': 'Odoo S.A.',
    'demo': [
        'data/demo_credentials.xml',
    ],
    'license': 'LGPL-3',
}

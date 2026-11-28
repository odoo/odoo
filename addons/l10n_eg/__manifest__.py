# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Egypt - Accounting",
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/egypt.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['eg'],
    'description': """
Egypt Accounting Module
==============================================================================
Egypt Accounting Basic Charts and Localization.

Activates:

- Chart of Accounts
- Taxes
- VAT Return
- Withholding Tax Report
- Schedule Tax Report
- Other Taxes Report
- Fiscal Positions
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'l10n_account_withholding_tax',
    ],
    'auto_install': ['account'],
    'post_init_hook': '_l10n_eg_post_init',
    'data': [
        'data/account_tax_report_data.xml',
        'data/ir_actions_server_data.xml',
        'views/account_tax.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_eg/static/src/css/report_invoice.css',
        ],
    },
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

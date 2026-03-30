# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Saudi Arabia - Accounting',
    'version': '2.0',
    'author': 'Odoo S.A., DVIT.ME',
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/16.0/applications/finance/fiscal_localizations/saudi_arabia.html',
    'description': """
Saudi Arabia Accounting Module
===========================================================
Saudi Arabia Accounting Basic Charts and Localization

Activates:

- Chart of Accounts
- Taxes
- Vat Filling Report
- Withholding Tax Report
- Fiscal Positions
""",
    'depends': [
        'l10n_multilang',
        'l10n_gcc_invoice',
    ],
    'data': [
        'data/account_data.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_group.xml',
        'data/l10n_sa_chart_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/report_paperformat_data.xml',
        'views/view_move_form.xml',
        'views/report_invoice.xml',
        'views/report_templates_views.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
    'license': 'LGPL-3',
}

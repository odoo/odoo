# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'United Arab Emirates - Accounting',
    'author': 'Odoo S.A.',
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/16.0/applications/finance/fiscal_localizations/united_arab_emirates.html',
    'description': """
United Arab Emirates Accounting Module
=======================================================
United Arab Emirates accounting basic charts and localization.

Activates:

- Chart of Accounts
- Taxes
- Tax Report
- Fiscal Positions
    """,
    'depends': ['base', 'account'],
    'data': [
        'data/l10n_ae_data.xml',
        'data/l10n_ae_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_group_data.xml',
        'data/l10n_ae_chart_post_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/fiscal_templates_data.xml',
        'data/account_chart_template_data.xml',
        'views/report_invoice_templates.xml',
        'views/account_move.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

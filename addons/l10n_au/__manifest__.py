# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Australia - Accounting',
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Australian Accounting Module
============================

Australian accounting basic charts and localizations.

Also:
    - activates a number of regional currencies.
    - sets up Australian taxes.
    """,
    'depends': ['account'],
    'data': [
        'data/l10n_au_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_data.xml',
        'data/account_tax_report_data.xml',
        'data/account.tax.group.csv',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_tax_template_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/res_currency_data.xml',
        'views/menuitems.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

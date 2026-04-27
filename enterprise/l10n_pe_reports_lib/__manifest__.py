# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Peru - Inventory and Balance Reports',
    'countries': ['pe'],
    "description": "5th and 6th Set Financial Reports. Inventory and Balance 3.1-3.7, 3.11-3.18, 3.20,3.24 and 3.25",
    "version": "1.0",
    "category": "Accounting/Localizations/Reporting",
    "website": "https://www.odoo.com/app/accounting",
    "license": "OEEL-1",
    "depends": [
        "l10n_pe_edi",
        "account_reports",
        "l10n_pe_reports",
        "l10n_pe_reports_stock",
    ],
    "data": [
        "data/l10n_pe_reports_lib.financial.rubric.csv",
        "views/l10n_pe_shareholder_views.xml",
        "views/l10n_pe_financial_rubric_views.xml",
        "views/account_account_views.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
}

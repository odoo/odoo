# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Odoo Mexican Localization Reports",
    'countries': ['mx'],
    "description": """
Electronic accounting reports
    - COA
    - Trial Balance

DIOT Report
    """,
    "version": "1.0",
    "author": "Vauxoo",
    "category": "Accounting/Localizations/Reporting",
    "website": "http://www.vauxoo.com",
    "license": "OEEL-1",
    "depends": [
        "account_reports",
        "l10n_mx",
        "l10n_mx_edi",
    ],
    "data": [
        "data/account_report_diot.xml",
        "data/country_data.xml",
        "data/templates/cfdicoa.xml",
        "data/templates/cfdibalance.xml",
        "views/res_country_view.xml",
        "views/res_partner_view.xml",
    ],
    "installable": True,
    "auto_install": ['l10n_mx', 'account_reports'],
}

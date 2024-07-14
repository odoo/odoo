# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Indian - GSTR India eFiling with POS",
    'countries': ['in'],
    "version": "1.0",
    "description": """
GSTR-1 return data set as per point of sale orders
    """,
    "category": "Accounting/Localizations/Reporting",
    "depends": ["l10n_in_reports_gstr", "point_of_sale"],
    'data': [
        'data/account_financial_html_report_gstr1.xml',
    ],
    "auto_install": True,
    "installable": True,
    "license": "OEEL-1",
}

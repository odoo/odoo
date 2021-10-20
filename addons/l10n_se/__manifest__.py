# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Swedish - Accounting",
    "version": "1.0",
    "summary": """Swedish chart of account EU BAS2020""",
    "description": """
This is the module to manage the accounting chart for Sweden in Odoo.
==============================================================================

Install some swedish chart of accounts.
    - Merge with XCLUDE CoA
    - Upgraded to EU BAS 2020 for Aktiebolag K2

    """,
    "author": "XCLUDE, Linserv AB",
    "website": "https://www.linserv.se",
    "category": "Localization",
    "depends": ["account", "base_vat"],
    "data": [
        "data/account_chart_template.xml",
        "data/account.account.template.csv",
        "data/account_chart_template_post_data.xml",
        "data/account_tax_group.xml",
        "data/account_tax_report_data.xml",
        "data/account_tax_template.xml",
        "data/account_fiscal_position_template.xml",
        "data/account_fiscal_position_account_template.xml",
        "data/account_fiscal_position_tax_template.xml",
        "data/account_chart_template_configuration.xml",
        "data/menuitem_data.xml",
    ],
    'license': 'LGPL-3',
    "installable": True,
}

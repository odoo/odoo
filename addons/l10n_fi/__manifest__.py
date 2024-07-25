# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Finnish Localization",
    "version": "13.0.2",
    "author": "Avoin.Systems, "
              "Tawasta, "
              "Vizucom, "
              "Sprintit",
    "category": "Accounting/Localizations/Account Charts",
    "description": """
This is the Odoo module to manage the accounting in Finland.
============================================================

After installing this module, you'll have access to :
    * Finnish chart of account
    * Fiscal positions
    * Invoice Payment Reference Types (Finnish Standard Reference & Finnish Creditor Reference (RF))
    * Finnish Reference format for Sale Orders

Set the payment reference type from the Sales Journal.
    """,
    "depends": [
        'account',
        'base_iban',
        'base_vat',
    ],
    "data": [
        'data/account_account_tag_data.xml',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_tax_report_line.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_template_data.xml',
        'data/l10n_fi_chart_post_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_chart_template_configuration_data.xml'
    ],
    "demo": [
        'demo/demo_company.xml',
    ],
    "installable": True,
    'license': 'LGPL-3',
}

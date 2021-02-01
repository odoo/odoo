# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2015 WT-IO-IT GmbH (https://www.wt-io-it.at)
#                    Mag. Wolfgang Taferner <wolfgang.taferner@wt-io-it.at>

# List of contributors:
# Mag. Wolfgang Taferner <wolfgang.taferner@wt-io-it.at>
# Josse Colpaert <jco@odoo.com>

{
    "name": "Austria - Accounting",
    "version": "3.0",
    "author": "WT-IO-IT GmbH, Wolfgang Taferner",
    "website": "https://www.wt-io-it.at",
    'category': 'Accounting/Localizations/Account Charts',
    'summary': "Austrian Standardized Charts & Tax",
    "description": """

Austrian charts of accounts (Einheitskontenrahmen 2010).
==========================================================

    * Defines the following chart of account templates:
        * Austrian General Chart of accounts 2010
    * Defines templates for VAT on sales and purchases
    * Defines tax templates
    * Defines fiscal positions for Austrian fiscal legislation
    * Defines tax reports U1/U30

    """,
    "depends": [
        "account",
        "base_iban",
        "base_vat",
    ],
    "data": [
        'data/res.country.state.csv',
        'data/account_account_tag.xml',
        'data/account_account_template.xml',
        'data/account_chart_template.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_template.xml',
        'data/account_chart_template_configure_data.xml',
    ],
}

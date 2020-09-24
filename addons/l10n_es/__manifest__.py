# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# List of contributors:
# Jordi Esteve <jesteve@zikzakmedia.com>
# Ignacio Ibeas <ignacio@acysos.com>
# Dpto. Consultoría Grupo Opentia <consultoria@opentia.es>
# Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Carlos Liébana <carlos.liebana@factorlibre.com>
# Hugo Santos <hugo.santos@factorlibre.com>
# Albert Cabedo <albert@gafic.com>
# Olivier Colson <oco@odoo.com>
# Roberto Lizana <robertolizana@trey.es>

{
    "name" : "Spain - Accounting (PGCE 2008)",
    "version" : "4.0",
    "author" : "Spanish Localization Team",
    'category': 'Accounting/Localizations/Account Charts',
    "description": """
Spanish charts of accounts (PGCE 2008).
========================================

    * Defines the following chart of account templates:
        * Spanish general chart of accounts 2008
        * Spanish general chart of accounts 2008 for small and medium companies
        * Spanish general chart of accounts 2008 for associations
    * Defines templates for sale and purchase VAT
    * Defines tax templates
    * Defines fiscal positions for spanish fiscal legislation
    * Defines tax reports mod 111, 115 and 303
""",
    "depends" : [
        "account",
        "base_iban",
        "base_vat",
    ],
    "data" : [
        'data/account_chart_template_data.xml',
        'data/account_group.xml',
        'data/account.account.template-common.csv',
        'data/account.account.template-pymes.csv',
        'data/account.account.template-assoc.csv',
        'data/account.account.template-full.csv',
        'data/account_chart_template_account_account_link.xml',
        'data/account_data.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}

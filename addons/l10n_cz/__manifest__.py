# -*- coding: utf-8 -*-

{
    'name': 'Czech - Accounting',
    'version': '1.0',
    'author': '26HOUSE',
    'website': 'http://www.26house.com',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Czech accounting chart and localization.  With Chart of Accounts with taxes and basic fiscal positions.

Tento modul definuje:

- Českou účetní osnovu za rok 2020

- Základní sazby pro DPH z prodeje a nákupu

- Základní fiskální pozice pro českou legislativu
    """,
    'depends': [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
          'data/l10n_cz_coa_data.xml',
          'data/account.account.template.csv',
          'data/account.group.template.csv',
          'data/l10n_cz_coa_post_data.xml',
          'data/account_data.xml',
          'data/account_tax_data.xml',
          'data/account_fiscal_position_data.xml',
          'data/account_chart_template_data.xml'
    ],
    'demo': ['data/demo_company.xml'],
    'license': 'LGPL-3',
}

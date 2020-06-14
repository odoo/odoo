# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2018 Linserv Aktiebolag, Sweden (<https://www.linserv.se>).

{
    'name': 'Swedish - Accounting',
    'version': '2.0',
    'summary': """Swedish chart of account EU BAS2020""",
    'description': """
This is the module to manage the accounting chart for Sweden in Odoo.
==============================================================================

Install some swedish chart of accounts.
    - Merge with EXCLUDE CoA
    - Upgraded to EU BAS 2020 for Aktiebolag K2
    - Auto set coutries list in group "Outside EU" to countries not part of country group "Europe"
        
    """,
    'author': 'EXCLUDE, Linserv AB',
    'website': 'https://www.linserv.se',
    'category': 'Localization',
    'category': 'Accounting/Localizations',
    'depends': [
        'account',
        'base_vat'
    ],
    'data': [
        'data/res_country_group.xml',
        'data/account_account_tag.xml',
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_post_data.xml',
        'data/account_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_template.xml',
        'data/account_fiscal_position_tax_template.xml',
        'data/account_fiscal_position_account_template.xml',
        'data/account_chart_template_data.xml',
        'data/menuitem_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
}

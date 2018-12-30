# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2009 Veritos - Jan Verlaan - www.veritos.nl

{
    'name' : 'Netherlands - Accounting',
    'version' : '2.0',
    'category': 'Localization',
    'description': """
This is the module to manage the accounting chart for Netherlands in Odoo.
=============================================================================
This module installs the a standard chart of accounts and also the Dutch Tax codes and
fiscal positions for deliveries inside and outside the UE.

In the company settings you can make the following settings:
- The number of digits of the chart of accounts. 
By default the chart of accounts are 6 digits. 4 is the minimum number of digits.
- If you want to use Anglosaxon acounting
- The prefix of the bank accounts, by default 1100
- The prefix of the cash account, by default 1000
- The way of rounding the VAT.

    """,
    'author'  : 'Veritos - Jan Verlaan',
    'website' : 'http://www.veritos.nl',
    'depends' : ['account',
                 'base_vat',
                 'base_iban',
    ],
    'data' : ['account_chart_netherlands.xml',
              "account_fiscal_position_template.xml",
              "account_fiscal_position_tax_template.xml",
              "account_fiscal_position_account_template.xml",
              "l10n_nl_account_chart.yml",
    ],
    'demo' : [],
    'installable': True,
}

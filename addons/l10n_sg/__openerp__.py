# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2014 Tech Receptives (<http://techreceptives.com>)

{
    'name': 'Singapore - Accounting',
    'version': '2.0',
    'author': 'Tech Receptives',
    'website': 'http://www.techreceptives.com',
    'category': 'Localization',
    'description': """
Singapore accounting chart and localization.
=======================================================

After installing this module, the Configuration wizard for accounting is launched.
    * The Chart of Accounts consists of the list of all the general ledger accounts
      required to maintain the transactions of Singapore.
    * On that particular wizard, you will be asked to pass the name of the company,
      the chart template to follow, the no. of digits to generate, the code for your
      account and bank account, currency to create journals.

    * The Chart of Taxes would display the different types/groups of taxes such as
      Standard Rates, Zeroed, Exempted, MES and Out of Scope.
    * The tax codes are specified considering the Tax Group and for easy accessibility of
      submission of GST Tax Report.

    """,
    'depends': ['base', 'account'],
    'demo': [ ],
    'data': [
             'l10n_sg_chart.xml',
             'l10n_sg_chart_tax.xml',
             'account_chart_template.yml',
    ],
    'installable': True,
    'post_init_hook': '_preserve_tag_on_taxes',
}

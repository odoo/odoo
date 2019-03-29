# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ireland - Accounting',
    'version': '1.0',
    'category': 'Localization',
    'description': """
    This module is for all the Irish SMEs who would like to setup their accounting and county codes quickly. The module provides:

    - a Chart of Accounts customised to Ireland
    - VAT Rates and Structure
    - IE Counties List (Make sure you don't already have any counties of Ireland in the system. Otherwise they will be duplicated)""",

    'author': 'Target Integration',
    'website': 'http://www.targetintegration.com',
    'depends': ['account', 'base_iban', 'base_vat'],
    'data': [
        'data/account_chart_template.xml',
        'data/account.account.template.csv',
        'data/account.chart.template.csv',
        'data/account_tax_data.xml',
        'data/res.country.state.csv',
        'data/account_chart_template_configuration_data.xml',
    ],
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) David Arnold (XOE Solutions).
# Author        David Arnold (XOE Solutions), dar@xoe.solutions
# Co-Authors    Juan Pablo Aries (devCO), jpa@devco.co
#               Hector Ivan Valencia Muñoz (TIX SAS)
#               Nhomar Hernandez (Vauxoo)
#               Humberto Ochoa (Vauxoo)

{
    'name': 'Colombian - Accounting',
    'version': '0.8',
    'category': 'Localization',
    'description': 'Colombian Accounting and Tax Preconfiguration',
    'author': 'David Arnold (XOE Solutions)',
    'website': 'https://xoe.solutions',
    'depends': [
        'account',
    ],
    'data': [
        'data/l10n_co_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_data.xml',
        'data/account.tax.group.csv',
        'data/account.tax.template.csv',
        'data/account_chart_template_configure_data.xml',
        'views/res_partner.xml',
    ],
}

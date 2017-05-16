# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) David Arnold (devCO).
# Author        David Arnold (devCO), dar@devco.co
# Co-Authors    Juan Pablo Aries (devCO), jpa@devco.co
#               Hector Ivan Valencia Muñoz (TIX SAS)
#               Nhomar Hernandez (Vauxoo)
#               Humberto Ochoa (Vauxoo)

{
    'name': 'Colombian Acounting - Old/Colgaap',
    'version': '0.9',
    'category': 'Localization',
    'description': 'Colombian colgaap only chart or accounts with tentative tax set',
    'author': 'David Arnold (DevCO Colombia)',
    'website': 'http://www.devco.co',
    'depends': ['l10n_co'],
    'data': [
        'data/account.account.tag.csv',
        'data/l10n_co_old_chart_data.xml',
        'data/account.account.template.csv',
        'data/account_chart_template_data.xml',
        'data/account.tax.template.csv',
        'data/account_chart_template_data.yml',
    ],
}

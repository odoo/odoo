# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2016 Onestein (<http://www.onestein.eu>).

{
    'name': 'Netherlands - Accounting',
    'version': '3.0',
    'category': 'Localization',
    'author': 'Onestein',
    'website': 'http://www.onestein.eu',
    'depends': [
        'account',
        'base_vat',
        'base_iban',
    ],
    'data': [
        'data/account_account_tag.xml',
        'data/account_chart_template.xml',
        'data/account.account.template.xml',
        'data/account_tax_template.xml',
        'data/account_fiscal_position_template.xml',
        'data/account_fiscal_position_tax_template.xml',
        'data/account_fiscal_position_account_template.xml',
        'data/account_chart_template.yml',
        'data/menuitem.xml',
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
}

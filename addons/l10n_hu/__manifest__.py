# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2014 InnOpen Group Kft (<http://www.innopen.eu>).
# Copyright (C) 2021 Odoo S.A.

{
    'name': 'Hungarian - Accounting',
    'version': '3.0',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Odoo S.A.',
    'description': """

Base module for Hungarian localization
==========================================

This module consists of:

 - Generic Hungarian chart of accounts
 - Hungarian taxes
 - Hungarian Bank information
 """,
    'depends': [
        'account'
    ],
    'data': [
        'data/l10n_hu_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',
        'data/account.tax.group.csv',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/account.fiscal.position.template.csv',
        'data/account.fiscal.position.tax.template.csv',
        'data/res.bank.csv',
        'data/account_chart_template_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/menuitem_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

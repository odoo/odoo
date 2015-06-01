# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2012 Thinkopen Solutions, Lda. All Rights Reserved
# http://www.thinkopensolutions.com.

{
    'name': 'Portugal - Chart of Accounts',
    'version': '0.011',
    'author': 'ThinkOpen Solutions',
    'website': 'http://www.thinkopensolutions.com/',
    'category': 'Localization/Account Charts',
    'description': 'Plano de contas SNC para Portugal',
    'depends': ['base',
                'base_vat',
                'account',
                ],
    'data': [
                   'account_types.xml',
                   'account_chart.xml',
                   'account_chart_template.xml',
                   'fiscal_position_templates.xml',
                   'account_taxes.xml',
                   'l10n_chart_pt_wizard.xml',
                   ],
    'demo': [],
    'installable': False,
}

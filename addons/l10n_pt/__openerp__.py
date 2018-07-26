# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2012 Thinkopen Solutions, Lda. All Rights Reserved
# http://www.thinkopensolutions.com.

{
    'name': 'Portugal - Accounting',
    'version': '0.011',
    'author': 'ThinkOpen Solutions',
    'website': 'http://www.thinkopensolutions.com/',
    'category': 'Localization',
    'description': 'Plano de contas SNC para Portugal',
    'depends': ['base',
                'base_vat',
                'account',
                ],
    'data': [
                   'account_chart.xml',
                   'account_chart_template.xml',
                   'fiscal_position_templates.xml',
                   'account_taxes.xml',
                   'account_chart_template.yml',
                   ],
    'demo': [],
    'installable': True,
}

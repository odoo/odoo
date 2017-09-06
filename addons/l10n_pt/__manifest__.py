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
                'account',
                'base_vat',
                ],
    'data': [
           'data/l10n_pt_chart_data.xml',
           'data/account_chart_template_data.xml',
           'data/account_fiscal_position_template_data.xml',
           'data/account_data.xml',
           'data/account_tax_data.xml',
           'data/account_chart_template_data.yml',
           ],
}

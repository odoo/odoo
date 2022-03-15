# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2012 Thinkopen Solutions, Lda. All Rights Reserved
# http://www.thinkopensolutions.com.

{
    'name': 'Portugal - Accounting',
    'version': '0.011',
    'author': 'ThinkOpen Solutions',
    'website': 'http://www.thinkopensolutions.com/',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Plano de contas SNC para Portugal',
    'depends': ['base',
                'account',
                'base_vat',
                ],
    'data': [
           'data/l10n_pt_chart_data.xml',
           'data/account_chart_template_data.xml',
           'data/account_fiscal_position_template_data.xml',
           'data/account_tax_group_data.xml',
           'data/account_tax_report.xml',
           'data/account_tax_data.xml',
           'data/account_chart_template_configure_data.xml',
           'data/l10n_pt_tax_exemption_reason_data.xml',
           'views/account_move_views.xml',
           'views/product_views.xml',
           'security/ir.model.access.csv',
           ],
    'license': 'LGPL-3',
}

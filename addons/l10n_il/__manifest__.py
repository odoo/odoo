# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Israel - Accounting',
    'version': '1.0',
    'category': 'Localization',
    'description': """
This is the latest basic Israelian localisation necessary to run Odoo in IL:
============================================================================

This module consists:
 - Generic Israelian chart of accounts
 - Israelian taxes
 """,
    'author': 'Odoo SA',
    'website': 'http://www.odoo.com/accounting',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_post_data.xml',
        'data/account_chart_template_configure_data.xml',
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
        'views/l10n_il_withh_tax_report_data_view.xml'
    ],
}

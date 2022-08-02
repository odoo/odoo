# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Thailand - Accounting',
    'version': '2.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Chart of Accounts for Thailand.
===============================

Thai accounting chart and localization.
    """,
    'author': 'Almacom',
    'website': 'http://almacom.co.th/',
    'depends': [
        'account_debit_note',
        'l10n_multilang',
    ],
    'data': [
        'data/account_tax_group_data.xml',
        'data/l10n_th_chart_data.xml',
        'data/account.account.template.csv',
        'data/l10n_th_chart_post_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_chart_template_data.xml',
        'views/res_partner_views.xml',
        'views/account_report.xml',
        'views/account_move_views.xml',
        'views/report_invoice.xml',
        'views/report_cash_voucher_templates.xml',
        'data/res.country.state.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_preserve_tag_on_taxes',
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Accounting',
    'version': '2.0',
    'description': """
Indian Accounting: Chart of Account.
====================================

Indian accounting chart and localization.

Odoo allows to manage Indian Accounting by providing Two Formats Of Chart of Accounts i.e Indian Chart Of Accounts - Standard and Indian Chart Of Accounts - Schedule VI.

Note: The Schedule VI has been revised by MCA and is applicable for all Balance Sheet made after
31st March, 2011. The Format has done away with earlier two options of format of Balance
Sheet, now only Vertical format has been permitted Which is Supported By Odoo.
  """,
    'category': 'Localization',
    'depends': [
        'account_tax_python',
    ],
    'data': [
        'data/account_data.xml',
        'data/l10n_in_chart_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_data.xml',
        'data/res_country_state_data.xml',
        'data/account_chart_template_data.yml',
        'views/product_template_view.xml',
        'views/report_invoice.xml',
        'views/res_company_view.xml',
        'views/res_country_state_view.xml',
        'views/res_partner_views.xml',
    ],
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Japan - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['jp'],
    'version': '2.3',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """

Overview:
---------

* Chart of Accounts and Taxes template for companies in Japan.
* This probably does not cover all the necessary accounts for a company. You are expected to add/delete/modify accounts based on this template.

Note:
-----

* Fiscal positions '内税' and '外税' have been added to handle special requirements which might arise from POS implementation. [1]  Under normal circumstances, you might not need to use those at all.

[1] See https://github.com/odoo/odoo/pull/6470 for detail.

    """,
    'author': 'Quartile Limited (https://www.quartile.co/)',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_report_jct_accumulation_form.xml',
        'data/account_report_jct_accumulation_schedule_1_3.xml',
        'data/account_report_jct_accumulation_schedule_2_3.xml',
        'data/account_report_jct_accumulation_schedule_4_3.xml',
        'data/account_report_jct_accumulation_schedule_5_3.xml',
        'data/account_report_jct_deduction_form.xml',
        'data/account_report_jct_deduction_schedule_1_3.xml',
        'data/account_report_jct_deduction_schedule_2_3.xml',
        'data/account_report_jct_deduction_schedule_4_3.xml',
        'data/account_report_jct_deduction_schedule_5_3.xml',
        'data/account_report_jct_return.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

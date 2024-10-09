# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Jordan - Accounting",
    'description': """
This is the base module to manage the accounting chart for Jordan in Odoo.
==============================================================================
    """,
    'author': "Odoo SA",
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.0',
    'depends': ['account', 'l10n_multilang'],
    'data': [
        'data/l10n_jo_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.group.csv',
        'data/account.tax.group.csv',
        'data/l10n_jo_chart_post_data.xml',
        'data/account_tax_report_data.xml',
        'data/account_tax_template_data.xml',
        'data/fiscal_templates_data.xml',
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml'
    ],
    'post_init_hook': 'load_translations',
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bulgaria - Accounting',
    'icon': '/l10n_bg/static/description/icon.png',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Odoo S.A.',
    'description': """
        Chart accounting and taxes for Bulgaria
    """,
    'depends': [
        'account', 'base_vat', 'l10n_multilang',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',
        'data/l10n_bg_chart_data.xml',
        'data/tax_report.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_template_data.xml',
        "data/account_fiscal_position_template.xml",
        'data/account_chart_template_configure_data.xml',
        'data/menuitem.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
    'license': 'LGPL-3',
}

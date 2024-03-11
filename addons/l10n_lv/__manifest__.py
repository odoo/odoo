{
    'name': "Latvia - Accounting",
    'version': '1.0.0',
    'description': """
        Chart of Accounts (COA) Template for Latvia's Accounting.
        This module also includes:
        * Tax groups,
        * Most common Latvian Taxes,
        * Fiscal positions,
        * Latvian bank list.

        author is Allegro IT (visit for more information https://www.allegro.lv)
        co-author is Chick.Farm (visit for more information https://www.myacc.cloud)
    """,
    'license': 'LGPL-3',
    'author': "Allegro IT, Chick.Farm",
    'website': "https://allegro.lv",
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'l10n_multilang',
        'account',
        'base_vat',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',
        'data/account_chart_template_setup_data.xml',
        'data/vat_tax_report.xml',
        'data/account_tax_group_data.xml',
        'data/account_tax_template_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_chart_template_load.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': 'load_translations',
}

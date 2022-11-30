{
    'name': 'Portugal - Accounting',
    'version': '1.0',
    'author': 'Odoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting',
    'depends': [
        'base',
        'account',
        'base_vat',
        'l10n_multilang',
    ],
    'data': [
           'data/l10n_pt_chart_data.xml',
           'data/account.account.template.csv',
           'data/account.group.template.csv',
           'data/account_chart_template_data.xml',
           'data/account_tax_group_data.xml',
           'data/account_tax_report.xml',
           'data/account_tax_data.xml',
           'data/account_fiscal_position_template_data.xml',
           'data/account_chart_template_configure_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

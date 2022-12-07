# -*- encoding: utf-8 -*-

{
    "name": "Tunisia - Accounting",
    "version": "1.0",
    "author": 'Odoo S.A.',
    "license": "LGPL-3",
    "category": 'Accounting/Localizations/Account Charts',
    "description": """
This is the module to manage the accounting chart for Tunisia in Odoo.
=======================================================================

""",
    "depends": ['base_vat', 'account'],
    "data": [
        'data/l10n_tn_chart_data.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',
        'data/account_chart_template_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/account_tax_group_data.xml',
        'data/tax_report.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}

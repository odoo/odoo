# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Poland - Accounting',
    'version' : '2.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the module to manage the accounting chart and taxes for Poland in Odoo.
==================================================================================

Module adds basic chart of account for Polish accounting, taxes and tags for JPK.

Niniejszy moduł jest przeznaczony dla odoo 16.0.

    """,
    'depends' : [
        'account',
        'base_iban',
        'base_vat',
    ],
    'data': [
            'data/accounting_tags.xml',
            'data/l10n_pl_chart_data.xml',
            'data/account.account.template.csv',
            'data/account.group.template.csv',
            'data/res.country.state.csv',
            'data/l10n_pl_chart_post_data.xml',
            'data/account_tax_group_data.xml',
            'data/account_tax_report_data.xml',
            'data/account_tax_data.xml',
            'data/account_fiscal_position_data.xml',
            'data/account_chart_template_data.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_preserve_tag_on_taxes',
    'license': 'LGPL-3',
}

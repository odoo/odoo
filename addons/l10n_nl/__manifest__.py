# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Netherlands - Accounting',
    'version': '3.1',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Onestein',
    'website': 'http://www.onestein.eu',
    'depends': [
        'base_iban',
        'base_vat',
        'account',
    ],
    'data': [
        'data/account_account_tag.xml',
        'data/account_tax_report_data.xml',
        'views/res_config_settings_view.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}

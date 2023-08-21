# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Portugal - Accounting (Deprecated - Use l10n_pt_account instead)',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pt'],
    'version': '1.0',
    'author': 'Odoo',
    'category': 'Accounting/Localizations/Account Charts',
    'description': 'Portugal - Accounting (Deprecated - Use l10n_pt_account instead)',
    'depends': [
        'base',
        'account',
        'base_vat',
    ],
    'license': 'LGPL-3',
    'data': [
        'data/account_tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
}

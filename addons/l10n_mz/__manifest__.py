# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mozambique - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'description': """
Mozambican Accounting localization
    """,
    'version': '1.0',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mz'],
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'base',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/tax_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

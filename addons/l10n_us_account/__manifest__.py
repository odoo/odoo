# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'United States - Accounting',
    'website': 'https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['us'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
    """,
    'depends': ['l10n_us', 'account'],
    'data': [
        'views/res_bank_views.xml',
    ],
    'installable': True,
    'auto_install': ['account'],
    'license': 'LGPL-3',
}

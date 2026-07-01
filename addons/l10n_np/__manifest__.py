# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nepal - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['np'],
    'description': """
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_chart_template_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

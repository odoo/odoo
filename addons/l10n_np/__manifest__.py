# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nepal - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['np'],
    'description': """
 Nepal - Accounting Chart and Tax Templates
    """,
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
    ],
    'data': [
        'data/account_chart_template_data.xml',
        'data/account.account.tag.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'post_init_hook': '_l10n_np_post_init',
}

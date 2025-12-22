# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'France - Localizations',
    'icon': '/account/static/description/l10n.png',
    'countries': ['fr'],
    'version': '2.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
""",
    'depends': [
        'base',
    ],
    'data': [
        'data/res_country_data.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'data/l10n_fr_demo.xml',
    ],
    'license': 'LGPL-3',
}

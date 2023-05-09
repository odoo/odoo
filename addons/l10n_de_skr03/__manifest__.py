# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Germany SKR03 - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['de'],
    'version': '3.1',
    'author': 'openbig.org',
    'website': 'http://www.openbig.org',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Dieses  Modul beinhaltet einen deutschen Kontenrahmen basierend auf dem SKR03.
==============================================================================

German accounting chart and localization.
    """,
    'depends': [
        'l10n_de',
        'account',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

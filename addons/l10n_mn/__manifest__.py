# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mongolia - Accounting',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations.html',
    'version': '1.1',
    'icon': '/account/static/description/l10n.png',
    'countries': ['mn'],
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'BumanIT LLC, Odoo S.A.',
    'description': """
This is the module to manage the accounting chart for Mongolia.
===============================================================

    * the Mongolia Official Chart of Accounts,
    * the Tax Code Chart for Mongolia
    * the main taxes used in Mongolia

Financial requirement contributor: Baskhuu Lodoikhuu. BumanIT LLC
""",
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account.account.tag.csv',
        'data/vat_report.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

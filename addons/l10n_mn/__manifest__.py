# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mongolia - Accounting',
    'version': '1.0',
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
    'data': [
        'data/account.account.tag.csv',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

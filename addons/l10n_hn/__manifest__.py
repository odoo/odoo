# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Honduras - Accounting',
    'version': '0.2',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Honduras.
====================================================================

Agrega una nomenclatura contable para Honduras. También incluye impuestos y la
moneda Lempira. -- Adds accounting chart for Honduras. It also includes taxes
and the Lempira currency.""",
    'author': 'Salvatore Josue Trimarchi Pinto',
    'website': 'http://bacgroup.net',
    'depends': [
        'base',
        'account',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

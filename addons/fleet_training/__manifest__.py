# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Fleet Training",
    'version': '20.0.1.0.0',
    'category': 'Fleet Training',
    'summary': "Manage a company vehicle fleet: vehicles, drivers, assignments and maintenance",
    'description': """
Fleet Training
==============
A teaching module built chapter by chapter to demonstrate the Odoo
Server Framework concepts (models, security, views, relations,
computed fields, constraints, inheritance, reports, wizards, ...)
on top of a realistic Fleet Management use case.
""",
    'author': "Odoo Training",
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.access.csv',
    ],
    'application': True,
}

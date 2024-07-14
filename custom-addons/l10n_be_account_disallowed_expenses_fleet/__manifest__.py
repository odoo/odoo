# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Disallowed Expenses Fleet',
    'countries': ['be'],
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Disallowed Expenses Fleet Data for Belgium
    """,
    'depends': ['account_disallowed_expenses_fleet', 'l10n_be_hr_payroll_fleet'],
    'data': ['views/fleet_vehicle_views.xml'],
    'installable': True,
    'website': 'https://www.odoo.com/app/accounting',
    'license': 'OEEL-1',
}

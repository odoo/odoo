# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Jobs on Contracts',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
This module allows you to define what is the default function of a specific user on a given account.
====================================================================================================

This is mostly used when a user encodes his timesheet: the values are retrieved
and the fields are auto-filled. But the possibility to change these values is
still available.

Obviously if no data has been recorded for the current account, the default
value is given as usual by the employee data so that this module is perfectly
compatible with older configurations.

    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['hr_timesheet_sheet'],
    'data': ['analytic_user_function_view.xml', 'security/ir.model.access.csv'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

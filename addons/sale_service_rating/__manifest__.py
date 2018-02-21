# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Service Rating',
    'category': 'Hidden',
    'description': """
This module allows a customer to give rating on task which are created from sales order.
""",
    'depends': [
        'rating_project',
        'sale_timesheet'
    ],
    'auto_install': True,
}

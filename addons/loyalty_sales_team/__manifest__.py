# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Loyalty Program for Sales Team',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Bridge Module for loyalty / sales_team',
    'description': 'Bridge Module to allow sales team managers to define loyalty programs',
    'depends': [
        'loyalty',
        'sales_team',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

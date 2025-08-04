# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
{
    'name': 'Stock Assigned Manual Moves View',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'SQL View for assigned stock moves to manual locations',
    'description': """SQL View for assigned stock moves to manual locations""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'depends': ['stock', 'base', 'sale','custom_odooship_decanting_process'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_assigned_manual_moves_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}


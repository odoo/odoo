# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Shiperoo Outbound Process',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Packing Process',
    'description': """Shiperoo Outbound Process.""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'depends': ['stock', 'base', 'sale', 'ash_test'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_inherit_views.xml',
        'wizard/pack_delivery_orders_wizard_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

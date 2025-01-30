# -*- coding: utf-8 -*-
{
    'name': 'Shiperoo Outbound Process',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Packing and Outbound Process',
    'description': """Shiperoo Outbound Process.""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'depends': ['stock', 'base', 'sale', 'ash_test'],
    'data': [
        'data/pack_app_sequence.xml',
        'security/ir.model.access.csv',
        'views/pc_totes_configuration_views.xml',
        'views/custom_pack_app_views.xml',
        'views/stock_picking_inherit_views.xml',
        'views/menuitem_view.xml',
        'wizard/custom_pack_app_wizard_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Shiperoo Decanting Process',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Barcode Support in Stock Picking.',
    'description': """Increase Quantity of Product by entering Barcode.""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'depends': ['stock', 'base'],
    'data': [
        'data/delivery_receipt_sequence.xml',
        'data/crate_container_configuration_data.xml',
        'security/ir.model.access.csv',
        'views/crate_container_configuration.xml',
        'views/crate_barcode_configuration.xml',
        'views/delivery_receipt_orders_views.xml',
        'views/automation_decanting_orders_process.xml',
        'views/license_plate_views.xml',
        'views/site_code_configuration_views.xml',
        'views/tenant_code_configuration_views.xml',
        'views/stock_picking_inherit_views.xml',
        'views/res_partner_inherit_views.xml',
        'views/menuitem_view.xml',
        'wizard/receipt_wizard_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

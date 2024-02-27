# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stock Transport',
    'summary': 'Stock Transport: Dispatch Management System',
    'description': 'Transport Management: organize packs in your fleet, or carriers.',
    'version': '1.0',
    'depends': ['stock_picking_batch', 'fleet'],
    'demo': [
        'data/fleet_vehicle_model_demo.xml',
        'data/stock_picking_batch_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_vehicle_model.xml',
        'views/stock_picking_batch.xml',
        'views/stock_batch_dock.xml',
        'views/stock_picking_type.xml',
        'views/stock_picking_view.xml',
    ],
    'license': 'LGPL-3',
}

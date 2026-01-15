# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stock Transport',
    'summary': 'Stock Transport: Dispatch Management System',
    'description': 'Transport Management: organize packs in your fleet, or carriers.',
    'version': '1.0',
    'depends': ['stock_picking_batch', 'fleet'],
    'demo': [
        'data/stock_fleet_demo.xml',
    ],
    'data': [
        'views/fleet_vehicle_model.xml',
        'views/stock_picking_batch.xml',
        'views/stock_picking_type.xml',
        'views/stock_picking_view.xml',
        'report/report_picking_batch.xml',
        'views/stock_location.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'post_init_hook': '_enable_dispatch_management',
}

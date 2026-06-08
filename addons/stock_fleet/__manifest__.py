# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stock Transport',
    'summary': 'Stock Transport Management',
    'description': 'Allows organizing deliveries by dock, assigning drivers and vehicles, and printing the associated consignment notes.',
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
        'report/report_picking_cmr.xml',
        'report/stock_fleet_reports.xml',
        'views/stock_location.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'post_init_hook': '_enable_dispatch_management',
    'assets': {
        'web.report_assets_common': [
            'stock_fleet/static/src/scss/report_picking_cmr.scss',
        ],
    },
}

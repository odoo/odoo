# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Field Service Repair',
    'summary':  'Allow user without repair right to access fsm stock.picking',
    'description': "Allow user without repair right to access fsm stock.picking",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['industry_fsm_stock', 'repair'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

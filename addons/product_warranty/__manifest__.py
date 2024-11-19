# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Lots/Serial Warranty Periods',
    'category': 'Inventory/Inventory',
    'depends': ['stock'],
    'description': """
Manage Warranty periods for Lots & Serial Numbers.
======================================================

Administrate Warranty periods in Inventory;
Define warranty period for each product variant;
Track warranty end date on Lot/Serial view per customer.
""",
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_warranty_views.xml',
        'report/stock_lot_customer.xml',
        'data/product_warranty_data.xml',
    ],
    'post_init_hook': '_enable_tracking_lots',
    'license': 'LGPL-3',
}

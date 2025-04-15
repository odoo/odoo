# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Delivery - Stock',
    'version': '1.0',
    'category': 'Inventory/Delivery',
    'description': """
Allows you to add delivery methods in pickings.
===============================================

When creating invoices from picking, the system is able to add and compute the shipping line.
""",
    'depends': ['sale_stock', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
        'views/delivery_view.xml',
        'views/delivery_portal_template.xml',
        'views/report_shipping.xml',
        'views/report_deliveryslip.xml',
        'views/report_package_barcode.xml',
        'wizard/choose_delivery_carrier_views.xml',
        'wizard/choose_delivery_package_views.xml',
        'views/stock_package_type_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_rule_views.xml',
        'views/stock_move_line_views.xml',
    ],
    'demo': ['data/delivery_demo.xml'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
    'post_init_hook': '_auto_install_sale_app',
}

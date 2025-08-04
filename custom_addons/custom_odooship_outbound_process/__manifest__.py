# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
{
    'name': 'Shiperoo Outbound Process',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Packing and Outbound Process',
    'description': """Shiperoo Outbound Process.""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'depends': ['stock', 'base', 'sale', 'ash_test', 'sale_stock'],
    'data': [
        'data/pack_app_sequence.xml',
        'data/shipping_retrying_log_scheduler.xml',
        'security/ir.model.access.csv',
        'views/pc_totes_configuration_views.xml',
        'views/custom_pack_app_views.xml',
        'views/stock_picking_inherit_views.xml',
        'views/sale_order_inherit_view.xml',
        'views/onetracker_config_view.xml',
        'views/post_pack_message_view.xml',
        'views/stock_picking_type_inherit_view.xml',
        'views/stock_route_inherit_view.xml',
        'views/shipping_integration_log_views.xml',
        'views/menuitem_view.xml',
        'wizard/custom_pack_app_wizard_view.xml',

    ],
    'assets': {
        'web.assets_backend': [
            'your_module_name/static/src/js/disable_pack_button.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

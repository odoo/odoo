# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Click & Collect",
    'version': '1.0',
    'category': 'Website/Website',
    'description': """
Allows customers to check in-store stock, pay on site, and pick up their orders at the shop.
""",
    'depends': ['base_geolocalize', 'payment_custom', 'website_sale_stock'],
    'data': [
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `payment_method_pay_on_site`.
        'data/product_product_data.xml',
        'data/delivery_carrier_data.xml',  # Depends on `product_pick_up_in_store`.

        'views/delivery_carrier_views.xml',
        'views/delivery_form_templates.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_warehouse_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_collect/static/src/**/*',
        ],
    },
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}

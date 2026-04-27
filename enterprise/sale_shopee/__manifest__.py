# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Shopee Connector",
    'summary': "Import Shopee orders and sync deliveries",
    'description': """
Import your Shopee orders in Odoo and synchronize deliveries
============================================================

Key Features
------------
* Import orders from multiple accounts and shops
* Orders are matched with Odoo products based on their internal reference (item_id or model_id in Shopee)
* Support for both Fulfillment by Shopee (FBS), Fulfillment by Merchant (FBM) and Fulfilled by Cross Border Seller (Hybrid):
* FBS: Importing the completed orders
* FBM/Hybrid: Delivery information is fetched from Shopee, track and synchronize the stock level to Shopee
""",
    'category': 'Sales/Sales',
    'sequence': 325,
    'application': True,
    'depends': [
        'sale_management',
        'stock_delivery',
    ],
    'data': [
        'data/mail_template_data.xml',
        'data/shopee_cron.xml',
        'data/shopee_data.xml',
        'security/ir.model.access.csv',
        'security/sale_shopee_security.xml',
        'views/sale_order_views.xml',
        'views/shopee_shop_views.xml',
        'views/shopee_account_views.xml',
        'views/shopee_item_views.xml',
        'views/stock_picking_views.xml',
        'views/menus.xml',
    ],
    'license': 'OEEL-1',
}

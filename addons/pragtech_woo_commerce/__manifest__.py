{
    'name': "Odoo WooCommerce Connector",
    'version': '16.0.1.1.27',
    'category': 'Services',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'www.pragtech.co.in',
    'summary': 'Odoo Woocommerce connector Woo Commerce import products export products import customers export customers import sales order export sales orders import tags export tags sync data word press wordpress connector woocommerce connector shopify',
    'description': """
        WooCommerce Connector
        ====================
        Odoo Woocommerce connector is used to import customers, products, sale-order from woocommerce to Odoo.
        This module has following features
        ----------------------------------
            1] Import/Export customer into Odoo/WooCommerce
            2] Import/Export product into Odoo/WooCommerce
            3] Import/Export product category into Odoo/WooCommerce
            4] Import/Export product attribute, values into Odoo/WooCommerce
            5] Import/Export product tags into Odoo/WooCommerce
            6] Import/Export sale-order into Odoo/WooCommerce
            7] Import/Export taxes into Odoo/WooCommerce
        
        <keywords>
        WooCommerce Connector
        Wordpress integration
        WooCommerce Integration
        Woo Commerce Sync Products
        Woo Commerce Sync Customers
        Woo Commerce Sync Sale Orders
        Import Export Pragmatic
    """,

    'depends': ['base', 'web', 'sale_management', 'purchase', 'stock', 'contacts', 'loyalty', 'delivery', 'hr_expense'],
    'external_dependencies': {
        'python': ['woocommerce','beautifulsoup4'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/account_tax_views.xml',
        'views/product_view.xml',
        'views/product_tag_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/product_attribute_view.xml',
        'views/product_attribute_value_view.xml',
        'views/product_category_views.xml',
        'views/woo_instance_views.xml',
        'views/woo_coupon_view.xml',
        'views/delivery_carrier_view.xml',
        'views/payment_acquirer_view.xml',
        'views/account_move_view.xml',
        'wizard/product_instance_view.xml',
        'wizard/inventory_instance_view.xml',
        'wizard/product_categ_instance_view.xml',
        'wizard/product_attr_instance_view.xml',
        'wizard/product_attr_value_instance_view.xml',
        'wizard/product_tag_instance_view.xml',
        'wizard/tax_instance_view.xml',
        'wizard/res_partner_instance_view.xml',
        'wizard/so_instance_view.xml',
        'wizard/product_variant_instance_view.xml',
        'views/woo_commerce_views.xml',
        'views/ir_cron.xml',
        'wizard/import_coupon_wizard_view.xml',
        'wizard/import_shipping_method_wizard_view.xml',
        'wizard/import_payment_gateway_wizard_view.xml',
        'wizard/import_order_refund_wizard_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pragtech_woo_commerce/static/src/scss/graph_widget.scss',
            'pragtech_woo_commerce/static/src/**/*.js',
            'pragtech_woo_commerce/static/src/**/*.xml',
            'pragtech_woo_commerce/static/src/css/product.css',
        ],
    },
    'images': ['static/description/img/woocommerce_connector.gif'],
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=odoo-woocomerce-connector',
    'currency': 'USD',
    'price': 0.0,  # 271
    'license': 'OPL-1',
    'active': False,
    'installable': True,
    'auto_install': False,
}

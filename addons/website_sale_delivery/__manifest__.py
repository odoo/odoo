{
    'name': 'eCommerce Delivery',
    'category': 'Website/Website',
    'summary': 'Add delivery costs to online sales',
    'version': '1.0',
    'description': """
Add a selection of delivery methods to your eCommerce store.
Configure your own methods with a pricing grid or integrate with carriers for a fully automated shipping process.
    """,
    'depends': ['website_sale', 'delivery', 'website_sale_stock'],
    'data': [
        'views/website_sale_delivery_templates.xml',
        'views/website_sale_delivery_views.xml',
        'views/res_config_settings_views.xml',
        'data/website_sale_delivery_data.xml'
    ],
    'demo': [
        'data/website_sale_delivery_demo.xml'
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_frontend': [
            'website_sale_delivery/static/src/**/*',
        ],
        'web.assets_tests': [
            'website_sale_delivery/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}

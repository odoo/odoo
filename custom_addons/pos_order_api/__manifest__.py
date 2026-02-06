{
    'name': 'POS Order API',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Laxya',
    'summary': 'API for Server-Side POS Order Creation',
    'description': """
        Core Service module to inject orders into POS.
        - Provides `pos.order.api` helper methods.
        - Handles Session validation and Tax Mapping.
        - Enforces Idempotency with UUIDs.
    """,
    'depends': ['point_of_sale', 'pos_self_order'],
    'data': [
        'data/ir_cron_data.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale.assets_prod': [
            'pos_order_api/static/src/xml/DeliveryToggle.xml',
            'pos_order_api/static/src/xml/RemoteOrderUI.xml',
            'pos_order_api/static/src/js/DeliveryToggle.js',
            'pos_order_api/static/src/js/RemoteOrderSync.js',
            'pos_order_api/static/src/css/DeliveryToggle.css',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

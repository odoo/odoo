{
    'name': 'POS Aggregator Gateway',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'author': 'Laxya',
    'summary': 'Webhook Gateway for UberEats and DoorDash',
    'description': """
        Receives Webhooks from Delivery Aggregators.
        - Normalizes JSON payloads.
        - Maps external IDs to Odoo IDs.
        - Calls pos_order_api to create orders.
    """,
    'depends': ['pos_order_api'],
    'data': [
        'security/ir.model.access.csv',
        'views/aggregator_config_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# API Paths
API_PATHS = {
    'production_singapore': 'https://partner.shopeemobile.com',
    'production_china': 'https://openplatform.shopee.cn',
    'production_brazil': 'https://openplatform.shopee.com.br',
    'test': 'https://openplatform.sandbox.test-stable.shopee.sg',
    'test_china': 'https://openplatform.sandbox.test-stable.shopee.cn',
}

# Mapping of Shopee API operations to their respective URL path, HTTP method, and API type
API_OPERATIONS_MAPPING = {
    'auth_partner': {
        'url_path': '/api/v2/shop/auth_partner',
        'api_type': 'public',
    },
    'refresh_token': {
        'url_path': '/api/v2/auth/access_token/get',
        'api_type': 'public',
    },
    'get_token': {
        'url_path': '/api/v2/auth/token/get',
        'api_type': 'public',
    },
    'get_shop_info': {
        'url_path': '/api/v2/shop/get_shop_info',
        'api_type': 'shop',
    },
    'get_order_list': {
        'url_path': '/api/v2/order/get_order_list',
        'api_type': 'order',
    },
    'get_order_detail': {
        'url_path': '/api/v2/order/get_order_detail',
        'api_type': 'order',
    },
    'get_shipping_parameter': {
        'url_path': '/api/v2/logistics/get_shipping_parameter',
        'api_type': 'logistics',
    },
    'ship_order': {
        'url_path': '/api/v2/logistics/ship_order',
        'api_type': 'logistics',
    },
    'get_tracking_number': {
        'url_path': '/api/v2/logistics/get_tracking_number',
        'api_type': 'logistics',
    },
    'create_shipping_document': {
        'url_path': '/api/v2/logistics/create_shipping_document',
        'api_type': 'logistics',
    },
    'get_shipping_document_result': {
        'url_path': '/api/v2/logistics/get_shipping_document_result',
        'api_type': 'logistics',
    },
    'download_shipping_document': {
        'url_path': '/api/v2/logistics/download_shipping_document',
        'api_type': 'logistics',
    },
    'update_stock': {
        'url_path': '/api/v2/product/update_stock',
        'api_type': 'product',
    },
}

# Mapping of Shopee fulfillment type to Shopee status to synchronize
ORDER_STATUSES_TO_SYNC = {
    'fbs': ['SHIPPED', 'COMPLETED'],
    'fbm': ['READY_TO_SHIP', 'PROCESSED'],
    'hybrid': ['READY_TO_SHIP', 'PROCESSED'],
}

# Mapping of fulfillment type names of Shopee API
FULFILLMENT_TYPE_MAPPING = {
    'fulfilled_by_shopee': 'fbs',
    'fulfilled_by_local_seller': 'fbm',
    'fulfilled_by_cb_seller': 'hybrid',
}
# Mapping of fulfillment type names of Shopee API
DELIVERY_STATUS_MAPPING = {
    'READY_TO_SHIP': 'draft',
    'PROCESSED': 'confirmed',
    'SHIPPED': 'done',
    'COMPLETED': 'done',
    'TO_CONFIRM_RECEIVE': 'done',
    'CANCELLED': 'cancelled',
    'RETRY_SHIP': 'error',
}

# Mapping of Shopee statuses to Odoo picking statuses
LOWER_SHIPPING_LABEL_MAPPING = {
    'NOT AVAILABLE': 'not available',
    'PROCESSING': 'processing',
    'READY': 'ready',
    'STORED': 'stored',
    'FAILED': 'failed',
}

# Mapping of Shopee Shop Statuses to Odoo Shop Statuses
SHOP_STATUS_MAPPING = {
    'NORMAL': 'active',
    'FROZEN': 'active',
    'BANNED': 'error',
}

# Shopee API's limits
ACCESS_TOKEN_EXPIRATION_THRESHOLD = 1
ORDER_LIST_DAYS_LIMIT = 15
ORDER_LIST_SIZE_LIMIT = 100
ORDER_DETAIL_SIZE_LIMIT = 50
SHIPPING_DOCUMENT_SIZE_LIMIT = 50
FETCH_SHIPPING_LABEL_SIZE_LIMIT = 50
CREATE_SHIPPING_LABEL_SIZE_LIMIT = 50

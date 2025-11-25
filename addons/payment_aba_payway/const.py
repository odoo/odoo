PAYMENT_METHODS_MAPPING = {
    'card': 'cards',
    'aba_khqr': 'abapay_khqr',
    'wechat_pay': 'wechat',
}

DEFAULT_PAYMENT_METHOD_CODES = {
    'card',
    'aba_khqr',
    'wechat_pay',
    'alipay',

    # Brand payment methods.
    'visa',
    'mastercard',
    'unionpay',
    'jcb',
}

PURCHASE_PAYMENT_SECURE_HASH_KEYS = [
    'req_time',
    'merchant_id',
    'tran_id',
    'amount',
    'items',
    'firstname',
    'lastname',
    'email',
    'phone',
    'type',
    'payment_option',
    'return_url',
    'continue_success_url',
    'currency',
    'custom_fields',
    'lifetime',
    'skip_success_page',
]

SUPPORTED_CURRENCIES = {
    'KHR',
    'USD',
}

CURRENCY_DECIMALS = {
    'KHR': 0,
    'USD': 2,
}

# Mapping of transaction states to PayWay success codes.
SUCCESS_CODE_MAPPING = {
    'done': (0,),
    'pending': (2,),
    'error': (3, 7),
}

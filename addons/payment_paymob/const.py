# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mapping of account's country codes to corresponding currency codes.
# Only 5 countries are supported and for each country the matching currency is required.
CURRENCY_MAPPING = {
    'AE': 'AED',
    'EG': 'EGP',
    'OM': 'OMR',
    'PK': 'PKR',
    'SA': 'SAR',
}

# Mapping of account's country codes to API URL prefixes.
API_MAPPING = {
    'AE': 'uae',
    'EG': 'accept',
    'OM': 'oman',
    'PK': 'pakistan',
    'SA': 'ksa',
}

# Mapping of Paymob's gateway types to Odoo payment method codes.
PAYMENT_METHODS_MAPPING = {
    'VPC': 'card',
    'MIGS': 'card',
    'UIG': 'mobile_wallet_eg',
    'CAGG': 'kiosk',
    'HALAN': 'halan',
    'SYMPL': 'sympl',
    'VALU': 'valu',
    'AMANV3': 'aman',
    'SOUHOOLAV3': 'souhoola',
    'CONTACT': 'contact',
    'PREMIUM6': 'premium_card',
    'FORSA': 'forsa',
    'TABBY': 'tabby',
    'TAMARA': 'tamara',
    'STCPAY': 'stcpay',
    'OMANNET': 'omannet',
    'EASYPAISADIRECT': 'easypaisa',
    'JAZZCASH': 'jazzcash',
}

# The codes of the payment methods to activate when Paymob is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'card',
}

# The fields to read from the response and order alphabetically to compute the signature.
SIGNATURE_FIELDS = [
    'amount_cents',
    'created_at',
    'currency',
    'error_occured',
    'has_parent_transaction',
    'id',
    'integration_id',
    'is_3d_secure',
    'is_auth',
    'is_capture',
    'is_refunded',
    'is_standalone_payment',
    'is_voided',
    'order',
    'owner',
    'pending',
    'source_data.pan',
    'source_data.sub_type',
    'source_data.type',
    'success',
]

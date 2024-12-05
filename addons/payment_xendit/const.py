# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Xendit, in ISO 4217 format.
SUPPORTED_CURRENCIES = [
    'IDR',
    'PHP',
    'THB',
    'MYR',
    'VND',
]

# To correctly allow lowest decimal place rounding
# https://docs.xendit.co/payment-link/payment-channels
CURRENCY_DECIMALS = {
    'IDR': 0,
}

# The codes of the payment methods to activate when Xendit is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    # ID
    'card',
    'dana',
    'ovo',
    'qris',
    # MY
    'fpx',
    'touch_n_go',
    # TH
    'promptpay',
    'linepay',
    'shopeepay',
    # VN
    'appota',
    'zalopay',
    'vnptwallet'

    # Brand payment methods.
    'visa',
    'mastercard',
}

# Mapping of payment code to channel code according to Xendit API
PAYMENT_METHODS_MAPPING = {
    'bank_bca': 'BCA',
    'bank_permata': 'PERMATA',
    'bpi': 'DD_BPI',
    'card': 'CREDIT_CARD',
    'maya': 'PAYMAYA',
    'wechat_pay': 'WECHATPAY',
    'scb': 'DD_SCB_MB',
    'krungthai_bank': 'DD_KTB_MB',
    'bangkok_bank': 'DD_BBL_MB',
    'touch_n_go': 'TOUCHNGO',
}

FPX_METHODS = [
    "DD_UOB_FPX", "DD_PUBLIC_FPX", "DD_AFFIN_FPX", "DD_AGRO_FPX", "DD_ALLIANCE_FPX",
    "DD_AMBANK_FPX", "DD_ISLAM_FPX", "DD_MUAMALAT_FPX", "DD_BOC_FPX", "DD_RAKYAT_FPX",
    "DD_BSN_FPX", "DD_CIMB_FPX", "DD_HLB_FPX", "DD_HSBC_FPX", "DD_KFH_FPX", "DD_MAYB2U_FPX", "DD_OCBC_FPX",
    "DD_RHB_FPX", "DD_SCH_FPX", "AFFIN_FPX_BUSINESS", "AGRO_FPX_BUSINESS",
    "ALLIANCE_FPX_BUSINESS", "AMBANK_FPX_BUSINESS", "ISLAM_FPX_BUSINESS", "MUAMALAT_FPX_BUSINESS", "BNP_FPX_BUSINESS",
    "CIMB_FPX_BUSINESS", "CITIBANK_FPX_BUSINESS", "DEUTSCHE_FPX_BUSINESS", "HLB_FPX_BUSINESS", "HSBC_FPX_BUSINESS",
    "RAKYAT_FPX_BUSINESS", "KFH_FPX_BUSINESS", "MAYB2E_FPX_BUSINESS", "OCBC_FPX_BUSINESS", "PUBLIC_FPX_BUSINESS", "RHB_FPX_BUSINESS",
    "SCH_FPX_BUSINESS", "UOB_FPX_BUSINESS"
]

# Mapping of transaction states to Xendit payment statuses.
PAYMENT_STATUS_MAPPING = {
    'draft': (),
    'pending': ('PENDING'),
    'done': ('SUCCEEDED', 'PAID', 'CAPTURED'),
    'cancel': ('CANCELLED', 'EXPIRED'),
    'error': ('FAILED',)
}

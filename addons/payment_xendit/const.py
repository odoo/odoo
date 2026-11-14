# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Xendit, in ISO 4217 format.
SUPPORTED_CURRENCIES = ["IDR", "MYR", "PHP", "SGD", "THB", "USD", "VND"]

# To correctly allow lowest decimal place rounding
# https://docs.xendit.co/payment-link/payment-channels
CURRENCY_DECIMALS = {"IDR": 0, "MYR": 0, "PHP": 0, "SGD": 0, "THB": 0, "USD": 0, "VND": 0}

# The codes of the default primary payment methods to activate
DEFAULT_PAYMENT_METHOD_CODES = {
    # ID
    "card",
    "dana",
    "ovo",
    "qris",
    # MY
    "fpx",
    "touch_n_go",
    # TH
    "promptpay",
    "linepay",
    "shopeepay",
    # VN
    "appota",
    "zalopay",
    "vnptwallet",
    # SG
    "paynow",
}

# FPX is an online payment method in Malaysia that allows customers to make payments directly from
# their bank accounts.
# Items suffixed with "_FPX" are for individual accounts.
# Items suffixed with "_BUSINESS" are for business accounts.
# When the user chooses FPX in Odoo, this list becomes filtered payment options in Xendit dashboard.
# When a webhook is received from Xendit, we can map all of these options back to 'fpx' in Odoo.
FPX_METHODS = [
    "UOB_FPX",
    "PUBLIC_FPX",
    "AFFIN_FPX",
    "AGRO_FPX",
    "ALLIANCE_FPX",
    "AMBANK_FPX",
    "ISLAM_FPX",
    "MUAMALAT_FPX",
    "BOC_FPX",
    "RAKYAT_FPX",
    "BSN_FPX",
    "CIMB_FPX",
    "HLB_FPX",
    "HSBC_FPX",
    "KFH_FPX",
    "MAYB2E_FPX",
    "MAYB2U_FPX",
    "OCBC_FPX",
    "RHB_FPX",
    "SCH_FPX",
    "AFFIN_FPX_BUSINESS",
    "AGRO_FPX_BUSINESS",
    "ALLIANCE_FPX_BUSINESS",
    "AMBANK_FPX_BUSINESS",
    "ISLAM_FPX_BUSINESS",
    "MUAMALAT_FPX_BUSINESS",
    "BNP_FPX_BUSINESS",
    "CIMB_FPX_BUSINESS",
    "CITIBANK_FPX_BUSINESS",
    "DEUTSCHE_FPX_BUSINESS",
    "HLB_FPX_BUSINESS",
    "HSBC_FPX_BUSINESS",
    "RAKYAT_FPX_BUSINESS",
    "KFH_FPX_BUSINESS",
    "MAYB2E_FPX_BUSINESS",
    "OCBC_FPX_BUSINESS",
    "PUBLIC_FPX_BUSINESS",
    "RHB_FPX_BUSINESS",
    "SCH_FPX_BUSINESS",
    "UOB_FPX_BUSINESS",
]

# Mapping of payment code to channel code according to Xendit API
PAYMENT_METHODS_MAPPING = {
    "bank_bca": "BCA_VIRTUAL_ACCOUNT",
    "bank_permata": "PERMATA_VIRTUAL_ACCOUNT",
    "bni": "BNI_VIRTUAL_ACCOUNT",
    "bri": "BRI_VIRTUAL_ACCOUNT",
    "bsi": "BSI_VIRTUAL_ACCOUNT",
    "cimb_niaga": "CIMB_VIRTUAL_ACCOUNT",
    "mandiri": "MANDIRI_VIRTUAL_ACCOUNT",
    "vietcapital": "VIETCAPITAL_VIRTUAL_ACCOUNT",
    "vpb": "VPB_VIRTUAL_ACCOUNT",
    "woori": "WOORI_VIRTUAL_ACCOUNT",
    "card": "CARDS",
    "maya": "PAYMAYA",
    "wechat_pay": "WECHATPAY",
    "scb": "SCB_MOBILE_BANKING",
    "krungthai_bank": "KTB_MOBILE_BANKING",
    "bangkok_bank": "BBL_MOBILE_BANKING",
    "touch_n_go": "TOUCHNGO",
    "paynow": "SGQR",
    "kfh": "KFH_FPX",
}

# Mapping of transaction states to Xendit payment statuses.
PAYMENT_STATUS_MAPPING = {
    "draft": (),
    "pending": ("PENDING", "ACTIVE", "REQUIRES_ACTION"),
    "done": ("SUCCEEDED", "COMPLETED"),
    "cancel": ("CANCELED", "EXPIRED"),
    "error": ("FAILED",),
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

API_URLS = {
    'production': {
        'pesopay': 'https://www.pesopay.com/b2c2/eng/payment/payForm.jsp',
        'siampay': 'https://www.siampay.com/b2c2/eng/payment/payForm.jsp',
        'bimopay': 'https://www.bimopay.com/b2c2/eng/payment/payForm.jsp',
        'paydollar': 'https://www.paydollar.com/b2c2/eng/payment/payForm.jsp',
    },
    'test': {
        'pesopay': 'https://test.pesopay.com/b2cDemo/eng/payment/payForm.jsp',
        'siampay': 'https://test.siampay.com/b2cDemo/eng/payment/payForm.jsp',
        'paydollar': 'https://test.paydollar.com/b2cDemo/eng/payment/payForm.jsp',
    }
}

# Mapping of currency ISO 4217 codes AsiaPay's currency codes.
# See https://www.paydollar.com/pdf/op/enpdintguide.pdf for the list of currency codes.
CURRENCY_MAPPING = {
    'AED': '784',
    'AUD': '036',
    'BND': '096',
    'CAD': '124',
    'CNY': '156',
    'EUR': '978',
    'GBP': '826',
    'HKD': '344',
    'IDR': '360',
    'INR': '356',
    'JPY': '392',
    'KRW': '410',
    'MOP': '446',
    'MYR': '458',
    'NZD': '554',
    'PHP': '608',
    'SAR': '682',
    'SGD': '702',
    'THB': '764',
    'TWD': '901',
    'USD': '840',
    'VND': '704',
}

# Mapping of both country codes (e.g., 'es') and IETF language tags (e.g.: 'fr-BE') to AsiaPay
# language codes. If a language tag is not listed, the country code prefix can serve as fallback.
LANGUAGE_CODES_MAPPING = {
    'en': 'E',
    'zh_HK': 'C',
    'zh_TW': 'C',
    'zh_CN': 'X',
    'ja_JP': 'J',
    'th_TH': 'T',
    'fr': 'F',
    'de': 'G',
    'ru_RU': 'R',
    'es': 'S',
    'vi_VN': 'S',
}

# Mapping of payment method codes to AsiaPay codes.
PAYMENT_METHODS_MAPPING = {
    'card': 'CC',
    'visa': 'VISA',
    'mastercard': 'Master',
    'jcs': 'JCB',
    'amex': 'AMEX',
    'diners': 'Diners',
    'payme': 'PayMe',
    'linepay': 'LINEPAY',
    'paymaya': 'PayMaya',
    'bpi': 'BPI',
    'gcash': 'GCash',
    'enets': 'ENETS',
    'enetsbanking': 'ENETSBANKING',
    'enetsqr': 'ENETSQR',
    'fps': 'FPS',
    'qris': 'QRIS',
    'duitnow': 'DuitNow',
    'ovo': 'OVO',
    'dana': 'DANA',
    'kredivo': 'KREDIVO',
    'touchngo': 'TouchnGo',
    'poli': 'POLI',
    'payid': 'PAYID',
    'humm': 'humm',
    'zippay': 'ZIPPAY',
    'hoolah': 'HOOLAH',
    'atome': 'ATOME',
    'pace': 'Pace',
    'shopeepay': 'SHOPEEPAY',
    'tendopay': 'TendoPay',
    'eximbay': 'Eximbay',
    'payu': 'PAYU',
    'truemoney': 'TRUEMONEY',
    'jkopay': 'JKOPAY',
}

# The keys of the values to use in the calculation of the signature.
SIGNATURE_KEYS = {
    'outgoing': [
        'merchant_id',
        'reference',
        'currency_code',
        'amount',
        'payment_type',
    ],
    'incoming': [
        'src',
        'prc',
        'successcode',
        'Ref',
        'PayRef',
        'Cur',
        'Amt',
        'payerAuth',
    ],
}

# Mapping of transaction states to AsiaPay success codes.
SUCCESS_CODE_MAPPING = {
    'done': ('0',),
    'error': ('1',),
}

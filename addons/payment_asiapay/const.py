# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
    'USD': '702',
    'VND': '704',
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

# Mapping of transaction states to AsiaPay success codes.
SUCCESS_CODE_MAPPING = {
    'done': ('0',),
    'error': ('1',),
}

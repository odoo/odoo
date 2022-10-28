# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Mapping IETF language tags (e.g.: 'fr-BE') to ECPay
# language codes. If a language tag is not listed, the country code prefix can serve as fallback.
LANGUAGE_CODES_MAPPING = {
    'en_US': 'ENG',
    'en_AU': 'ENG',
    'en_CA': 'ENG',
    'en_IN': 'ENG',
    'en_GB': 'ENG',
    'ja_JP': 'JPN',
    'ko_KP': 'KOR',
    'ko_KR': 'KOR',
    'zh_CN': 'CHI',
    'zh_HK': '',
    'zh_TW': '',
}

# Mapping of transaction states to ECPay success codes.
SUCCESS_CODE_MAPPING = {
    'done': ('1',),
    'pending': ('2', '10100073',),
}

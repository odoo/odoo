API_URLS = {
    'production': {
        'merchant': 'https://merchant.api.bancontact.net',
        'jwks': 'https://jwks.bancontact.net',
        'qrcode': 'https://qrcodegenerator.api.bancontact.net/qrcode',
    },
    'preprod': {
        'merchant': 'https://merchant.api.preprod.bancontact.net',
        'jwks': 'https://jwks.preprod.bancontact.net',
        'qrcode': 'https://qrcodegenerator.api.preprod.bancontact.net/qrcode',
    },
}


SUPPORTED_CURRENCIES = ("EUR",)

ISS_KEY = "https://payconiq.com/iss"
ISS_VALUE = "Payconiq"
IAT_KEY = "https://payconiq.com/iat"
JTI_KEY = "https://payconiq.com/jti"
PATH_KEY = "https://payconiq.com/path"
SUB_KEY = "https://payconiq.com/sub"

JWKS_TTL = 12
MAX_SKEW_SECONDS = 60

# Base URL for Payconiq API in preproduction (test) environment
API_URL = "https://merchant.api.preprod.bancontact.net"

# Payconiq only supports payments in euros
SUPPORTED_CURRENCIES = ("EUR",)

# List of countries in the European Economic Area where Payconiq can be used
SUPPORTED_COUNTRIES = (
    "BE",  # Belgium
    "AT",  # Austria
    "BG",  # Bulgaria
    "HR",  # Croatia
    "CY",  # Cyprus
    "CZ",  # Czech Republic
    "DK",  # Denmark
    "EE",  # Estonia
    "FI",  # Finland
    "FR",  # France
    "GR",  # Greece
    "HU",  # Hungary
    "IE",  # Ireland
    "IT",  # Italy
    "LV",  # Latvia
    "LT",  # Lithuania
    "LU",  # Luxembourg
    "MT",  # Malta
    "NL",  # Netherlands
    "PL",  # Poland
    "PT",  # Portugal
    "RO",  # Romania
    "SK",  # Slovakia
    "SI",  # Slovenia
    "ES",  # Spain
    "SE",  # Sweden
)

# Critical JOSE headers used for JWS validation in Payconiq callbacks
ISS_KEY = "https://payconiq.com/iss"
ISS_VALUE = "Payconiq"
IAT_KEY = "https://payconiq.com/iat"
JTI_KEY = "https://payconiq.com/jti"
PATH_KEY = "https://payconiq.com/path"
SUB_KEY = "https://payconiq.com/sub"

# URL to fetch Payconiq's public JWKs
JWKS_URL = "https://jwks.preprod.bancontact.net"

# Time (in hours) to cache the JWKS to avoid frequent network requests
JWKS_TTL = 12

# QR Generator
QR_GENERATOR_URL = "https://qrcodegenerator.api.preprod.bancontact.net/qrcode?f=PNG&s=%s&c=https://payconiq.com/l/1/%s/pm%s"

# Payconiq Callback
BASE_CALLBACK_URL = "https://equal-lizard-newly.ngrok-free.app"

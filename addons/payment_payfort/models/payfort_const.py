# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYFORT_SUCCESS = [
    "02",  # Authorization success
    "04",  # Capture success
    "06",  # Refund success
    "08",  # Authorization voided successfully
    "12",  # Check status success
    "14",  # Purchase succes
    "18",  # Tokenization success
    "44",  # 3DS success
    "52",  # Token created successfully
]
PAYFORT_ERROR = [
    "00",  # Invalid request
    "03",  # Authorization failed
    "05",  # Catpure failed
    "07",  # Refund failed
    "10",  # Incomplete
    "09",  # Authorization void failed
    "11",  # Check status failed
    "13",  # Purchase failure
    "17",  # Tokenization failed
    "45",  # 3DS failed
]
# all the exponent factors for minor units that are different than 2 as described in ISO-4217
# note that they may not all be supported by payfort, i just followed the ISO spec
CURRENCY_DEC_MAP = {
    "BIF": 0,
    "CLP": 0,
    "DJF": 0,
    "GNF": 0,
    "ISK": 0,
    "JPY": 0,
    "KMF": 0,
    "KRW": 0,
    "PYG": 0,
    "RWF": 0,
    "UGX": 0,
    "UYI": 0,
    "VND": 0,
    "VUV": 0,
    "XAF": 0,
    "XOF": 0,
    "XPF": 0,
    "BHD": 3,
    "IQD": 3,
    "JOD": 3,
    "KWD": 3,
    "LYD": 3,
    "OMR": 3,
    "TND": 3,
    "CLF": 4,
    "UYW": 4,
}

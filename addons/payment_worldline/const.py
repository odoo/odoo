# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple

# Supported payment methods
PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'code'])
PAYMENT_METHOD_TYPES = [
    PMT('bancontact', ['BE'], ['EUR'], 3012),
    PMT('eps', ['AT'], ['EUR'], 5406),
    PMT('ideal', ['NL'], ['EUR'], 809),
    PMT('p24', ['DE', 'PL'], ['PLN'], 3124),
]

# Mapping of transaction states to Worldline's payment statuses.
# See https://docs.direct.worldline-solutions.com/en/integration/api-developer-guide/statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': (
        'CREATED', 'REDIRECTED', 'AUTHORIZATION_REQUESTED', 'PENDING_CAPTURE', 'CAPTURE_REQUESTED'
    ),
    'done': ('CAPTURED',),
    'cancel': ('CANCELLED',),
    'declined': ('REJECTED', 'REJECTED_CAPTURE'),
}

# Mapping of response codes indicating Worldline handled the request
# See https://apireference.connect.worldline-solutions.com/s2sapi/v1/en_US/json/response-codes.html.
VALID_RESPONSE_CODES = {
    200: 'Successful',
    201: 'Created',
    402: 'Payment Rejected',
}

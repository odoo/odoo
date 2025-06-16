# Part of Odoo. See LICENSE file for full copyright and licensing details.

PAYMENT_METHOD_TYPES = [
    {'name': 'bancontact', 'countries': ['BE'], 'currencies': ['EUR'], 'code': 3012},
    {'name': 'eps', 'countries': ['AT'], 'currencies': ['EUR'], 'code': 5406},
    {'name': 'ideal', 'countries': ['NL'], 'currencies': ['EUR'], 'code': 809},
    {'name': 'p24', 'countries': ['DE', 'PL'], 'currencies': ['PLN'], 'code': 3124},
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

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple


# Support payment method types
PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'recurrence'])
PAYMENT_METHOD_TYPES = [
    PMT('card', [], [], 'recurring'),
    PMT('ideal', ['nl'], ['eur'], 'punctual'),
    PMT('bancontact', ['be'], ['eur'], 'punctual'),
    PMT('eps', ['at'], ['eur'], 'punctual'),
    PMT('giropay', ['de'], ['eur'], 'punctual'),
    PMT('p24', ['pl'], ['eur', 'pln'], 'punctual'),
]

# Mapping of transaction states to Stripe {Payment,Setup}Intent statuses.
# See https://stripe.com/docs/payments/intents#intent-statuses for the exhaustive list of status.
INTENT_STATUS_MAPPING = {
    'draft': ('requires_payment_method', 'requires_confirmation', 'requires_action'),
    'pending': ('processing',),
    'done': ('succeeded',),
    'cancel': ('canceled',),
}

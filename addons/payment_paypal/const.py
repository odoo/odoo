# Part of Odoo. See LICENSE file for full copyright and licensing details.

# ISO 4217 codes of currencies supported by PayPal
# See https://developer.paypal.com/docs/reports/reference/paypal-supported-currencies/.
# Last seen on: 22 September 2022.
SUPPORTED_CURRENCIES = (
    'AUD',
    'BRL',
    'CAD',
    'CNY',
    'CZK',
    'DKK',
    'EUR',
    'HKD',
    'HUF',
    'ILS',
    'JPY',
    'MYR',
    'MXN',
    'TWD',
    'NZD',
    'NOK',
    'PHP',
    'PLN',
    'GBP',
    'RUB',
    'SGD',
    'SEK',
    'CHF',
    'THB',
    'USD',
)

# The codes of the payment methods to activate when Paypal is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'paypal',
}

# Mapping of transaction states to PayPal payment statuses
# See https://developer.paypal.com/docs/api-basics/notifications/ipn/IPNandPDTVariables/
PAYMENT_STATUS_MAPPING = {
    'pending': ('Pending',),
    'done': ('Processed', 'Completed', 'Cleared'),  # cleared status is required fo echeck
    'cancel': ('Voided', 'Expired'),
}

# PAYPAL_CLIENT_ID='ATR-C4I_pBxt_sBRoIf-Fycy4xSN8byPdujgzeYiFi8xza3bBug83xHRhTzoNeN6BW9ewCRNbOT_yfbz'
# PAYPAL_CLIENT_SECRET='EDV7Ft605Mt-adZfBc5AetlsyV8HcUVilNcHgi7Mg7gqCnvXp3Bf8mtzSQ85pAloFgOFvbRgZsyscBeN'

PAYPAL_CLIENT_ID='AWfClPjf6ZGUf9vpa06Un6RT4e0v4PA4m_6VzXHaGY_rZqeL8QtI5vcvZCrcyicnI7nMXiq0jVfofSGJ'
PAYPAL_CLIENT_SECRET='EOhwGOoQEglBaWER7Y-JrcAGIKRfRlbieSgbNt_IJfcvHVpNAUIsmzq-P6kCm52ycpeEjlaXYMnwL-5k'

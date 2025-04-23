# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The codes of the payment methods to activate when Buckaroo is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    'ideal',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]

# Mapping of payment method codes to Buckaroo codes.
# https://docs.buckaroo.io/docs/payment-methods
# For each payment method check "Requests" tab and get "Services.ServiceList.Name"
# in "Example request"
PAYMENT_METHODS_MAPPING = {
    'alipay': 'Alipay',
    'apple_pay': 'applepay',
    'bancontact': 'bancontactmrcash',
    'belfius': 'belfius',
    'billink': 'Billink',
    'card': 'mastercard',
    'cartes_bancaires': 'CarteBancaire',
    'eps': 'eps',
    'giropay': 'GiroPay',
    'in3': 'Capayable',
    'ideal': 'ideal',
    'kbc': 'KBCPaymentButton',
    'bank_reference': 'PayByBank',
    'p24': 'Przelewy24',
    'paypal': 'paypal',
    'poste_pay': 'PostePay',
    'sepa_direct_debit': 'SepaDirectDebit',
    'sofort': 'sofortueberweisung',
    'tinka': 'Tinka',
    'trustly': 'Trustly',
    'wechat_pay': 'WeChatPay',
    'klarna': 'klarna',
    'afterpay_riverty': 'afterpay',
}

# Mapping of transaction states to Buckaroo status codes.
# See https://www.pronamic.nl/wp-content/uploads/2013/04/BPE-3.0-Gateway-HTML.1.02.pdf for the
# exhaustive list of status codes.
STATUS_CODES_MAPPING = {
    'pending': (790, 791, 792, 793),
    'done': (190,),
    'cancel': (890, 891),
    'refused': (690,),
    'error': (490, 491, 492,),
}

# The currencies supported by Buckaroo, in ISO 4217 format.
# See https://support.buckaroo.eu/frequently-asked-questions
# Last seen online: 7 November 2022.
SUPPORTED_CURRENCIES = [
    'EUR',
    'GBP',
    'PLN',
    'DKK',
    'NOK',
    'SEK',
    'CHF',
    'USD',
]

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Currencies supported by Xendit
SUPPORTED_CURRENCIES = [
    'IDR', 'PHP'
]

API_URL_OBJ = {
    "INVOICE": "https://api.xendit.co/v2/invoices",
    "TOKEN": "https://api.xendit.co/credit_card_tokens/{token_id}",
    "CHARGE": "https://api.xendit.co/credit_card_charges",
}

STATUS_MAPPING = {
    'draft': (),
    'pending': ('PENDING',),
    'authorized': ('AUTHORIZED',),
    'done': ('SUCCEEDED', 'CAPTURED', 'PAID', 'REQUESTED', 'SETTLED'),
    'cancel': ('CANCELLED', 'EXPIRED'),
    'error': ('FAILED',)
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Payfast only operates in South Africa with ZAR.
SUPPORTED_CURRENCIES = ("ZAR",)

# URLs used depending on the environment (live/test).
PAYFAST_URLS = {"live": "https://www.payfast.co.za", "test": "https://sandbox.payfast.co.za"}

# Base URL and version of Payfast's account-level API (refunds, subscriptions, ...), which is
# separate from the checkout/ITN flow above and not available in Sandbox mode.
# https://developers.payfast.co.za/api
PAYFAST_API_URL = "https://api.payfast.co.za"
PAYFAST_API_VERSION = "v1"

# `subscription_type` value that sets up a payment for on-demand tokenized charges (as opposed to
# `1`, a Payfast-scheduled subscription with its own frequency/cycles, which Odoo does not model).
# https://developers.payfast.co.za/docs#tokenization
TOKENIZATION_SUBSCRIPTION_TYPE = "2"

# Mapping of Odoo payment method codes to the `payment_method` value expected by Payfast.
# Only covers codes with a matching `payment.method` record in `data/payment_method_data.xml`;
# Payfast also accepts a few others (debit_card, masterpass, store_card) that aren't exposed here
# for lack of a distinct icon to represent them with in Odoo's checkout.
# https://developers.payfast.co.za/docs#step_1_form_fields
PAYMENT_METHODS_MAPPING = {
    "eft": "ef",
    "card": "cc",
    "mobicred": "mc",
    "scode": "sc",
    "snapscan": "ss",
    "zapper": "zp",
    "moretyme": "mt",
    "mukuru": "mu",
    "apple_pay": "ap",
    "samsung_pay": "sp",
    "capitec_pay": "cp",
    "absa_pay": "ab",
    "google_pay": "gp",
    "nedbank_eft": "nd",
    "payflex": "pf",
}

# Fields that must be included, in this exact order, when generating the signature.
# https://developers.payfast.co.za/docs#step_2_signature
SIGNATURE_FIELDS_ORDER = [
    "merchant_id",
    "merchant_key",
    "return_url",
    "cancel_url",
    "notify_url",
    "name_first",
    "name_last",
    "email_address",
    "cell_number",
    "m_payment_id",
    "amount",
    "item_name",
    "item_description",
    "custom_int1",
    "custom_int2",
    "custom_int3",
    "custom_int4",
    "custom_int5",
    "custom_str1",
    "custom_str2",
    "custom_str3",
    "custom_str4",
    "custom_str5",
    "email_confirmation",
    "confirmation_address",
    "payment_method",
    "subscription_type",
    "billing_date",
    "recurring_amount",
    "frequency",
    "cycles",
    "subscription_notify_email",
    "subscription_notify_webhook",
    "subscription_notify_buyer",
]

# Valid domains from which an ITN (webhook) notification can originate.
VALID_NOTIFICATION_HOSTS = [
    "www.payfast.co.za",
    "w1w.payfast.co.za",
    "w2w.payfast.co.za",
    "sandbox.payfast.co.za",
]

DEFAULT_PAYMENT_METHOD_CODES = ["card"]

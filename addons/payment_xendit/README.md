# Xendit

## Technical details

APIs:
- [Payment Sessions API](https://docs.xendit.co/apidocs/create-session) (`/sessions`)
- [Payment Requests API](https://docs.xendit.co/apidocs/create-payment-request) version `3`
- [Payment Tokens API](https://docs.xendit.co/apidocs/create-payment-token) version `3`
- Credit Charge API version `1` (`/credit_card_charges`, legacy: only used to charge tokens saved
  before the migration to the Payment Tokens API, as Xendit provides no migration path for them)

This module uses the generic payment with redirection flow based on form submission provided by the
`payment` module for every payment method, including `Card`: the customer is redirected to a
Xendit-hosted payment link created through the Payment Sessions API, and Xendit notifies Odoo of the
outcome through a webhook.

For `Card` payments, if the customer opts to save the payment method, the Payment Tokens API token
Xendit returns on a successful payment is saved in Odoo. Charging a saved token is done
server-to-server through the Payment Requests API; if that requires 3-D Secure authentication, the
customer is redirected to the authentication URL Xendit returns.

A customer returning from checkout, or from a 3-D Secure challenge, is checked directly against
Xendit before falling back to the default pending state, in case the webhook notification is delayed
or dropped.

## Supported features

- Payment with redirection flow for all payment methods, including `Card`
- Webhook notifications
- Tokenization with or without payment
- Status sync when the customer returns from checkout

## Module history

- `18.0`
  - The redirect flow is migrated to Xendit's Payment Sessions and Payment Requests/Tokens v3 APIs;
    the inline `Card` form, the Xendit.js SDK, and the `xendit_public_key` credential (kept on
    existing databases for backward compatibility, but no longer used) are dropped. odoo/odoo#277626
- `17.4`
  - The support for tokenization via `Card` is added. odoo/odoo#158445
- `17.0`
  - The first version of the module is merged. odoo/odoo#141661

## Testing instructions

https://docs.xendit.co/apidocs/simulate-payment-test-mode

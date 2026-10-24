# Payfast

## Technical details

API: [Payfast API](https://developers.payfast.co.za/api)

API Backend: [Payfast Internal Odoo APIs](https://www.odoo.com/odoo/project/4106/tasks/6317924)

This module integrates Payfast using the generic payment with redirection flow based on form
submission provided by the `payment` module.

Payfast exposes two distinct integrations: the classic form-based checkout/ITN flow, signed with
a fixed field order and `merchant_id`/`merchant_key`; and a separate JSON-based account-level API
used for charging tokenized (recurring) payments, authenticated with its own
header-based signature scheme (`merchant-id`/`version`/`timestamp`/`signature`, fields sorted
alphabetically). Both signatures rely on the same passphrase, which is required for tokenized
payments.

## Supported features

- Payment with redirection flow
- Webhook notifications (ITN)
- Tokenization with payment

## Not implemented features

- Refunds initiated from Odoo

## Module history

- `20.0`
  - The first version of the module is merged.

## Testing instructions

https://developers.payfast.co.za/docs#sandbox


Notes:
- An HTTPS connection is required for testing.

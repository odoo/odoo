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

- Refunds initiated from Odoo: Payfast's refund API requires a preliminary query call to
  determine the refund method, and often requires the buyer's own bank account details (holder,
  bank, branch code, account number) when a refund to the original payment source isn't
  available; refunds must be processed from the Payfast dashboard instead.
- Payfast's native recurring subscriptions (own frequency/cycles/pause/cancel): tokenized
  payments only use Payfast's on-demand (ad hoc) charge, driven by Odoo's own subscription
  scheduling.

## Module history

- `20.0`
  - The first version of the module is merged.

## Testing instructions

https://developers.payfast.co.za/docs#sandbox


Notes:
- The Instant Transaction Notification (ITN) requires a publicly reachable `notify_url`; when
  testing locally, expose the server with a tunnel (e.g. ngrok) and set `web.base.url` to the
  tunnel's HTTPS address before starting a payment.
- Tokenized (recurring) charges *are* testable in Sandbox: complete a payment with the "Save my
  payment details" checkbox ticked, then trigger a charge on the resulting token.

# ECPay

## Technical details

API: [ECPay AIO (All-In-One) Checkout API](https://developers.ecpay.com.tw/?p=16427) version `V5`

This module integrates ECPay using the generic payment with redirection flow based on form
submission provided by the `payment` module.

The outgoing request is a POST form submitted to the ECPay-hosted payment page. ECPay handles the
full payment experience (method selection, data entry) and notifies Odoo of the outcome via two
independent channels:

- **Return URL** (`/payment/ecpay/return`): ECPay redirects the customer back to Odoo after the
  payment is completed. Both `GET` (deferred payment methods such as CVS or ATM) and `POST`
  (immediate payment methods) are supported.
- **Webhook** (`/payment/ecpay/webhook`): ECPay sends a server-to-server `POST` notification in
  parallel. The `SimulatePaid` flag is checked to skip test simulation notifications.

Both channels verify the `CheckMacValue` signature (SHA-256 over URLencoded sorted parameters
sandwiched by `HashKey` and `HashIV`) before processing the payment data.

Payment method filtering is implemented via the `IgnorePayment` parameter: all ECPay-level methods
that don't map to the selected Odoo payment method are excluded, nudging the customer toward the
expected option on the ECPay page.

## Supported features

- Payment with redirection flow
- Webhook notifications
- Multiple payment methods:
  - Credit/debit card (Visa, Mastercard, JCB, UnionPay)
  - Bank transfer
  - WeChat Pay
  - CVS (convenience stores: 7-Eleven, FamilyMart, Hi-Life, OK Mart)
  - Mobile wallets (JKO Pay, iPASS Money)
  - TWQR
- Single-currency support for `TWD`

## Not implemented features

- Manual capture
- Refunds
- Tokenization

## Module history

- `19.0`
  - The first version of the module is merged. odoo/odoo#235069

## Testing instructions

Docs: https://developers.ecpay.com.tw/16447

Use the ECPay stage environment (the module is configured to target
`https://payment-stage.ecpay.com.tw` when in `test` state).

A ready-to-use sandbox merchant account, its `HashKey` / `HashIV` credentials and test card numbers are published in
the ECPay developer documentation linked above.

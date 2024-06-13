# Demo

## Technical details

This module does not integrate with an API and, instead, allows for fake payments that can be made
to test applications' payment flows without API credentials nor payment method details.

## Supported features

- Direct payment flow
- Tokenization with our without payment
- Full and partial manual capture
- Full and partial refunds
- Express checkout
- Select the outcome of the payment

## Module history

- `17.0`
  - The support for express checkout is added. odoo/odoo#113644
  - The support for customer fees is removed as it is no longer supported by the `payment` module.
    odoo/odoo#132104
- `16.3`
  - The support for partial manual capture is added. odoo/odoo#117356
- `16.0`
  - The module is renamed from `payment_test` to `payment_demo`. odoo/odoo#99397
  - The support for manual capture, full and partial refunds, customer fees, and the selection of
    the payment outcome are added. odoo/odoo#78083

## Testing instructions

The Demo payment provider can only be used in test mode.

No payment method details are required and the outcome of payments can be chosen. If provided, the
"Payment Details" are used as display name for the created payment tokens.

# Flutterwave

## Technical details

API: [Flutterwave standard](https://developer.flutterwave.com/docs/collecting-payments/standard/)
version `3`

This module integrates Flutterwave using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications
- Tokenization with payment

## Not implemented features

- Manual capture
- Refunds

## Module history

- `15.4`
  - The first version of the module is merged. odoo/odoo#85514

## Testing instructions

https://developer.flutterwave.com/docs/integration-guides/testing-helpers

### MasterCard

**Card Number**: `5531886652142950`

**Expiry Date**: `09/32`

**CVC Code**: `564`

**OPT**: `12345`

# Mollie

## Technical details

API: [Payments API](https://docs.mollie.com/reference/v2/payments-api/create-payment) version `2`

This module integrates Mollie using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications

## Not implemented features

- Tokenization
- Manual capture
- Refunds

## Module history

- `15.0`
  - The first version of the module is merged. odoo/odoo#74136

## Testing instructions

An HTTPS connection is required.

https://docs.mollie.com/overview/testing

**Card Number**: `4111111111111111`

**Expiry Date**: `123`

**CVC Code**: `123`

# Amazon Payment Services

## Technical details

API: [Redirection API](https://paymentservices-reference.payfort.com/docs/api/build/index.html#redirection)

This module integrates Amazon Payment Services using the generic payment with redirection flow based
on form submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications

## Not implemented features

- [Tokenization with or without payment](https://paymentservices-reference.payfort.com/docs/api/build/index.html#safe-tokenization)

## Module history

- `16.0`
  - The first version of the module is merged. odoo/odoo#95860

## Testing instructions

https://paymentservices.amazon.com/docs/EN/12.html

### VISA

**Card Number**: `4111111111111111`

**Expiry Date**: any date in the future

**CVC Code**: any

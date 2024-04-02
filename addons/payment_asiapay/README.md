# AsiaPay

## Technical details

API: Client Post Through Browser version `3.67`

This module integrates AsiaPay using the generic payment with redirection flow based on form
submission provided by the `payment` module.

The entire API reference and the integration guide can be found on the
[Integration Guide](https://www.paydollar.com/pdf/op/enpdintguide.pdf).

## Supported features

- Payment with redirection flow
- Webhook notifications

## Not implemented features

- Manual capture
- Full and partial refunds
- Express checkout
- Multi-currency processing

## Module history

- `16.0`
  - The first version of the module is merged. odoo/odoo#98441

## Testing instructions

### VISA

**Card Number**: `4335900000140045`

**Expiry Date**: `07/2030`

**CVC Code**: `123`

**Name**: `testing card`

**3DS Password**: `password`

# Worldline

## Technical details

API: [Worldline Direct API](https://docs.direct.worldline-solutions.com/en/api-reference)
version `2`

This module integrates Worldline using the generic payment with redirection flow based on form
submission provided by the `payment` module.

This is achieved by following the [Hosted Checkout Page]
(https://docs.direct.worldline-solutions.com/en/integration/basic-integration-methods/hosted-checkout-page)
guide.

## Supported features

- Payment with redirection flow
- Webhook notifications
- Tokenization with payment

## Not implemented features

- Tokenization without payment
- Manual capture
- Refunds

## Module history

- `18.0`
  - The first version of the module is merged. odoo/odoo#175194.

## Testing instructions

https://docs.direct.worldline-solutions.com/en/integration/how-to-integrate/test-cases/index

Use any name, any date in the future, and any 3 or 4 digits CVC.

### VISA

**Card Number**: `4330264936344675`

### 3D Secure 2 (VISA)

**Card Number**: `4874970686672022`

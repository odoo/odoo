# Worldline

## Technical details

API: [Worldline Direct API](https://docs.direct.worldline-solutions.com/en/api-reference)
version `1`

## Supported features

- Payment with redirection flow
- Webhook notifications
- Tokenization with payment

## Not implemented features

- Tokenization without payment
- Manual capture
- Refunds

## Module history

- `saas-17.5`
  - The first version of the module is merged. odoo/odoo#TODO EDM

## Testing instructions

https://docs.direct.worldline-solutions.com/en/integration/how-to-integrate/test-cases/index

Use any name, any date in the future, and any 3 or 4 digits cvc

### VISA

**Card Number**: `4330264936344675`


### 3D Secure 2 (VISA)

**Card Number**: `4874970686672022`

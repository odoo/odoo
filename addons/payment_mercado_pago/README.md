# Mercado Pago

## Technical details

APIs:
- [Checkout Pro](https://www.mercadopago.com.mx/developers/en/docs/checkout-pro/overview)
- [Checkout API](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/overview)
- [Checkout Bricks](https://www.mercadopago.com.mx/developers/en/docs/checkout-bricks/overview)

This module integrates Mercado Pago using a combination of "Checkout Pro", "Checkout API", and
"Checkout Bricks" APIs.

The card payment method uses the "Card Payment Brick" to enable direct payments, while other payment
methods use the generic payment with redirection flow based on form submission provided by the
`payment` module. Redirect payments send the same request payload as Checkout Pro's JavaScript SDK
would. The remaining API calls are made to the Checkout API. It was not possible to only integrate
the redirect flow with Checkout Pro as it only allows redirecting customers to the payment page, nor
with only the Checkout API only as it requires building a custom payment form to accept direct
payments from the merchant's website.

## Supported features

- Payment with redirection flow
- Tokenization
- OAuth authentication

## Not implemented features

- [Manual capture](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-management/capture-authorized-payment)
- [Full and partial refunds](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-management/cancellations-and-refunds)

## Module history

- `19.0`
  - OAuth support is added in addition to the credentials-based authentication. odoo/odoo#194998
  - Support for tokenization is added. odoo/odoo#194998
- `16.0`
  - The first version of the module is merged. odoo/odoo#83957

## Testing instructions

https://www.mercadopago.com.mx/developers/en/docs/checkout-api/additional-content/your-integrations/test/cards

### VISA

**Card Number**: `4075595716483764`

**Expiry Date**: any future date

**Security Code**: any

**Card holder**: `APRO`

**Email**: `test_user_[0-9]@testuser.com`

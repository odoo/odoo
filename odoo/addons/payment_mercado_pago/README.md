# Mercado Pago

## Technical details

APIs:
- [Checkout Pro](https://www.mercadopago.com.mx/developers/en/docs/checkout-pro/landing)
- [Checkout API](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/landing)

This module integrates Mercado Pago using a combination of "Checkout Pro" and "Checkout API". The
generic payment with redirection flow based on form submission provided by the `payment` module is
used to initiate the payment with the same request payload as Checkout Pro's JavaScript SDK would.
The remaining API calls are made to the Checkout API. It was not possible to only integrate with
Checkout Pro as it only allows redirecting customers to the payment page, nor with only the Checkout
API only as it requires building a custom payment form to accept direct payments from the merchant's
website.

## Supported features

- Payment with redirection flow
- Webhook notifications

## Not implemented features

- [Manual capture](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-management/capture-authorized-payment)
- [Full and partial refunds](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-management/cancellations-and-refunds)

## Module history

- `16.0`
  - The first version of the module is merged. odoo/odoo#83957

## Testing instructions

https://www.mercadopago.com.mx/developers/en/docs/checkout-api/additional-content/your-integrations/test/cards

### VISA

**Card Number**: `4075595715555555`

**Expiry Date**: `11/25`

**Security Code**: `123`

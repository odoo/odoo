# Buckaroo

## Technical details

API: [Buckaroo Payment Engine](https://www.pronamic.nl/wp-content/uploads/2013/04/BPE-3.0-Gateway-HTML.1.02.pdf)
version `3.0`

This module integrates Buckaroo using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow

## Not implemented features

- Webhook notifications

## Module history

- `15.2`
  - The support for webhook notifications is added. odoo/odoo#82922

## Testing instructions

Buckaroo's hosted payment page allows to simulate payments and select the outcome without any
payment details when selecting the payment method PayPal.

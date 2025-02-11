# Nuvei

## Technical details

API: [Payment Page API](https://docs.nuvei.com/documentation/accept-payment/payment-page/quick-start-for-payment-page/)

This module integrates Nuvei using the generic payment with redirection flow based
on form submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications

## Not implemented features


## Module history

- `18.0`
  - The first version of the module is merged. odoo/odoo#181459

## Testing instructions
Card Transactions:
For transactions *above* 99 you must use the 3D-Secure cards listed here: 
https://docs.nuvei.com/documentation/integration/testing/testing-cards/#3d-secure-v2-test-scenarios
(You must match the card number and cardholder name to what is listed in frictionless/etc depending
on what you are testing and then follow the expiration date/security code information from below)

### VISA (Up to $99)
**Card Number:** 4761 3441 3614 1390
**Expiry Date:** Any date in the future
**Security Code:** 123


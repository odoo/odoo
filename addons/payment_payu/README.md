# PayU

## Technical details

API: [PayU Hosted Checkout](https://docs.payu.in/docs/prebuilt-checkout-page-integration)

This module integrates PayU using the generic payment with redirection flow based on form
submission provided by the payment module.

## Supported features

- Payment with redirection flow
- OAuth authentication

## Module history

- `19.0`
  - The first version of the module is merged. odoo/odoo#267962

## Testing instructions

https://docs.payu.in/docs/test-cards-upi-id-and-wallets

### VISA

**Card Number**: `4012001037141112`

**Expiry Date**: any date in the future

**CVC Code**: any

**OTP**: `123456`

### MasterCard

**Card Number**: `5123456789012346`

**Expiry Date**: any date in the future

**CVC Code**: any

**OTP**: `123456`

### UPI

**UPI ID**: `anything@payu`

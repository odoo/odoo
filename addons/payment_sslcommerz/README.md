# SSLCOMMERZ

## Technical details

API: [SSLCOMMERZ Hosted Checkout API](https://developer.sslcommerz.com/doc/v4/)

This module integrates SSLCOMMERZ using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- IPN notification

## Not implemented features

- Refunds

## Module history

- `20.0`
  - The first version of the module is merged. odoo/odoo#269048

## Testing instructions

https://developer.sslcommerz.com/doc/v4/#payment-process-environment

### VISA

**Card Number**: `4111111111111111`

**Expiry Date**: `12/26`

**CVC Code**: `111`

**Mobile OTP**: `111111` or `123456`

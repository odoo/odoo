# Razorpay

## Technical details

API: [Hosted Checkout](https://razorpay.com/docs/payments/payment-gateway/web-integration/hosted)
version `1`

## Supported features

- Payment with redirection flow
- Webhook notifications
- Manual capture
- Partial refunds

## Not implemented features

- Tokenization with the Recurring Payments API

## Module history

- `16.0`
  - The first version of the module is merged. odoo/odoo#92848

## Testing instructions

https://razorpay.com/docs/payments/payments/test-card-upi-details/

A valid Indian phone number must be set on the partner. Example: `+91123456789`

### VISA

**Card Number**: `4111111111111111`

**Expiry Date**: any future date

**Card Secret**: any

**OTP**: `1111`

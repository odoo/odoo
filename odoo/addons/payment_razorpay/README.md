# Razorpay

## Technical details

API: [Recurring Payments API](https://razorpay.com/docs/api/payments/recurring-payments/)
version `1`

## Supported features

- Direct payment flow
- Webhook notifications
- Full manual capture
- Partial refunds

## Not implemented features

- Partial manual capture

## Module history

- `17.0`
  - The previous Hosted Checkout API that allowed for redirect payments is replaced by the Recurring
    Payments API that supports direct payments and tokenization. odoo/odoo#143525
- `16.0`
  - The first version of the module is merged. odoo/odoo#92848

## Testing instructions

https://razorpay.com/docs/payments/payments/test-card-upi-details/

https://razorpay.com/docs/payments/payments/test-upi-details/

A valid Indian phone number must be set on the partner. Example: `+91123456789`

### VISA

**Card Number**: `4111111111111111`

**Expiry Date**: any future date

**Card Secret**: any

**OTP**: `1111`

### UPI

**UPI ID**: `success@razorpay` or `failure@razorpay`

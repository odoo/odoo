# Stripe

## Technical details

SDK: [Stripe.js](https://stripe.com/docs/js) version `3`

API: [Stripe API](https://stripe.com/docs/api) version `2019-05-16`

This module integrates Stripe using a custom implementation of the payment with redirection flow: no
redirect form is rendered and, instead, a Checkout Session object is created from the server before
the customer is redirected to the session's payment page from the front-end. This is achieved by
following the [Stripe-hosted page](https://stripe.com/docs/checkout/quickstart) guide.

The module also offers a quick onboarding thanks to the Stripe Connect platform solution.

## Supported features

- Payment with redirection flow
- Webhook notifications
- Tokenization with or without payment
- Quick onboarding

## Not implemented features

- Manual capture
- Full and partial refunds
- Express checkout

## Module history

- `15.0`
  - A new button is added to create a webhook automatically. odoo/odoo#79621
  - The support for the Stripe Connect onboarding flow is added. odoo/odoo#79621
- `14.3`
  - The previous direct payment flow that was supported by the SetupIntent API is replaced by a
    payment with redirection flow using the Checkout API. odoo/odoo#141661

## Testing instructions

https://stripe.com/docs/testing

**Card Number**: `4111111111111111`

**Expiry Date**: any future date

**CVC Code**: any

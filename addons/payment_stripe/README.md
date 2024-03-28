# Stripe

## Technical details

SDK: [Stripe.js](https://stripe.com/docs/js) version `3`

API: [Stripe API](https://stripe.com/docs/api) version `2019-05-16`

This module relies on the Web Elements SDK to render the list of available payment methods and their
payment detail inputs on the payment form. The JS and CSS assets of the SDK are loaded on the pages
where the form is visible using a script tag.

When the Web Elements need to fetch/push information from/to Stripe or when a payment operation
(e.g., refund, offline payment) is executed from the backend, a server-to-server API call is made to
the appropriate API endpoint.

This is achieved by following the [Collect payment details before creating an Intent]
(https://docs.stripe.com/payments/accept-a-payment-deferred) guide. It is preferred over the
recommended "Payment Element" where payment intent is created beforehand because the
`payment.transaction` object doesn't exist yet when the form is rendered, so we don't have any
reference to communicate to Stripe. Also, all the methods to create Stripe objects
(e.g., intents or customers) are defined on the `payment.transaction`​ object.

The module also offers a quick onboarding thanks to the Stripe Connect platform solution.

## Supported features

- Direct payment flow
- Webhook notifications
- Tokenization with or without payment
- Full manual capture
- Full and partial refunds
- Express checkout

## Not implemented features

- Partial manual capture

## Module history

- `16.4`
  - The previous Checkout API that allowed for redirect payments is replaced by the Payment Intents
    API that supports direct payments. odoo/odoo#123573
  - The support for eMandates for recurring payments is added. odoo/odoo#123573
  - The responses of webhook notifications are sent with the proper HTTP code. odoo/odoo#117940
- `16.0`
  - Stripe uses the payment methods set up on the account when none are assigned to the payment
    provider in Odoo, instead of only offering the "Card" payment method. odoo/odoo#107647
  - The support for express checkout is added. odoo/odoo#88374
- `15.4`
  - The support for full and partial refunds is added. odoo/odoo#92235
- `15.3`
  - Webhook notifications accept three new events based on the PaymentIntent and SetupIntent objects
    in place of the `checkout.session.completed` event to handle async payment status updates.
    odoo/odoo#84150
  - The support for manual capture is added. odoo/odoo#69598
- `15.2`
  - An HTTP 404 "Forbidden" error is raised instead of a Validation error when the authenticity of
    the webhook notification cannot be verified. odoo/odoo#81607
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

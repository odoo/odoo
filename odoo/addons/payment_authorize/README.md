# Authorize.net

## Technical details

SDK: [Accept.js](https://developer.authorize.net/api/reference/features/acceptjs.html) version `1`

API: [Accept suite API](https://developer.authorize.net/api/reference/index.html) version `1`

This module renders a self-hosted payment form with regular (non iframe) inputs and relies on the
Accept.js SDK to send the payment details to Authorize.net through a secure connection. The JS
assets are loaded in JavaScript when the payment form is submitted.

Other communications with Authorize.net are performed via server-to-server API calls.

This combined solution allows the implementation of a simple direct payment flow whilst keeping the
front-end development efforts low. As payment details are retrieved in clear but are immediately
passed to the Accept.js SDK, the solution qualifies for SAQ A-EP.

## Supported features

- Direct payment flow
- Tokenization with or without payment
- Full manual capture
- Full refunds

## Missing features

- Partial manual capture
- Webhook notifications: not available

## Module history

- `16.1`
  - The "Authorize Currency" field is replaced by the generic "Currencies" field of `payment`.
    odoo/odoo#101018
- `16.0`
  - Archiving a token no longer deactivates the related payment method on Authorize. odoo/odoo#93774
- `15.4`
  - The support for full refunds is added. odoo/odoo#92279
- `15.0`
  - Support for ACH payments is added. odoo/odoo#75289
- `14.3`
  - The payment with redirection flow that existed alongside the direct payment flow is dropped.
    odoo/odoo#141661

## Testing instructions

An HTTPS connection is required.

https://developer.authorize.net/hello_world/testing_guide.html

## VISA

**Card Number**: `4111111111111111`

## MasterCard

**Card Number**: `5424000000000015`

## eCheck

**Bank Name**: whatever

**Name On Account**: whatever

**Account Number**: `123456`

**ABA Routing Number**: `121122676`

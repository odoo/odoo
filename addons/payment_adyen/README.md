# Adyen

## Technical details

SDK: Web Drop-in
version `6.9.0`

APIs:

- [Checkout API](https://docs.adyen.com/api-explorer/Checkout/) version `71`
~~- [Recurring API](https://docs.adyen.com/api-explorer/Recurring/) version `49`~~

This module relies on the Web Drop-in SDK to render the list of available payment methods and their
payment detail inputs on the payment form. The JS and CSS assets of the SDK are loaded directly from
the `__manifest__.py` file.

When the Web Drop-in needs to fetch/push information from/to Adyen or when a payment operation
(e.g., refund, offline payment) is executed from the backend, a server-to-server API call is made to
the appropriate API endpoint.

This combined solution allows the implementation of a good-quality direct payment flow whilst
keeping the front-end development efforts low. The 3DS support is also entirely delegated to Adyen.

This is achieved by following Web Drop-in's
"[Advanced flow](https://docs.adyen.com/online-payments/build-your-integration/advanced-flow/?platform=Web&integration=Drop-in)".
It is preferred over the recommended "Sessions flow" that only requires dealing with the `/sessions`
endpoint instead of three `/payment/*` endpoints because two of those are still required to
implement tokenization and handle 3DS redirects.

## Supported features

- Direct payment flow
- Webhook notifications
- Tokenization with or without payment
- Manual capture
- Full and partial refunds

## Not implemented features

- Express checkout

## Module history

- `16.0`
  - Archiving a token no longer deactivates the related payment method on Adyen. odoo/odoo#93774
- `15.3`
  - The support for manual capture is added. odoo/odoo#70591
- `15.2`
  - An HTTP 404 "Forbidden" error is raised instead of a Validation error when the authenticity of
    the webhook notification cannot be verified. odoo/odoo#81607
- `15.0`
  - The support for both full and partial refunds is added. odoo/odoo#70881
  - The Web Drop-in SDK is migrated to version 4.7.3 and the Checkout API to version 67 to switch
    from relying on origin keys and use client keys instead. odoo/odoo#74827
- `14.3`
  - The previous Hosted Payment Pages API that allowed for redirect payments is replaced by a
    combination of the Web Drop-in SDK (version 3.9.4) and the Checkout (version 53) and Recurring
    (version 49) APIs. odoo/odoo#141661

## Testing instructions

https://docs.adyen.com/development-resources/testing/test-card-numbers/

### VISA

**Card Number**: `4111111145551142`

**Expiry Date**: `03/30`

**CVC Code**: `737`

### 3D Secure 2

**Card Number**: `5454545454545454`

**Expiry Date**: `03/30`

**CVC Code**: `737`

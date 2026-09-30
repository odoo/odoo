# PayPal

## Technical details

API: [PayPal Standard Checkout](https://developer.paypal.com/studio/checkout/standard)

SDK: [JavaScript SDK](https://developer.paypal.com/sdk/js/reference/)

This module relies on the "Javascript" SDK to render the PayPal payment button in place of the
generic payment form's submit button. The assets of the SDK are loaded dynamically when a payment
method is selected.

When the PayPal button is clicked, a server-to-server API call is made to create the order on PayPal
side and a PayPal modal is opened. When the order is confirmed within the modal, another call is
made to finalize the payment.

## Supported features

- Direct payment flow
- Webhook notifications

## Module history

- `18.0`
  - The NVP/SOAP API that allowed for redirect payments is replaced by a combination of the
    JavaScript SDK and the Standard Checkout API. odoo/odoo#167402
- `17.0`
  - The support for customer fees is removed as it is no longer supported by the `payment` module.
    odoo/odoo#132104
- `16.2`
  - The "Merchant Account ID" and "Use IPN" fields are removed. odoo/odoo#104974
- `16.1`
  - Customer fees are converted into the currency of the payment transaction. odoo/odoo#100156
- `15.2`
  - An HTTP 404 "Forbidden" error is raised instead of a Validation error when the authenticity of
    the webhook notification cannot be verified. odoo/odoo#81607

## Testing instructions

Payments must be made using a separate [sandbox account](https://www.sandbox.paypal.com/myaccount/).

Read more at https://developer.paypal.com/tools/sandbox/.

# Xendit

## Technical details

APIs:
- [Invoices API](https://developers.xendit.co/api-reference/#create-invoice) version `2`
- [Credit Charge API](https://developers.xendit.co/api-reference/#create-charge) version `1`

SDK: [Xendit.js](https://docs.xendit.co/credit-cards/integrations/tokenization)

This module integrates Xendit with different payment flows depending on the payment method:

- For `Card` payments, it renders a self-hosted payment form with regular (non-iframe) inputs and 
  relies on the Xendit.js SDK to create a (single-use or multiple-use) token that is used to make
  the payment. When the payment is successful, and the user opts to save the payment method, the
  token is saved in Odoo. Other communications with Xendit are performed via server-to-server API
  calls.

  The JS assets are loaded in JavaScript when the payment form is submitted.

  As payment details are retrieved in clear but are immediately passed to the Xendit.js SDK, the
  solution qualifies for SAQ A-EP.

- For other payment methods, this module uses the generic payment with redirection flow based on
  form submission provided by the `payment` module.

This implementation allows supporting tokenization for `Card` payments whilst retaining support for
other payment methods via the redirection flow.

## Supported features

- Direct Payment flow for `Card` payment methods
- Payment with redirection flow for other payment methods
- Webhook notifications
- Tokenization with or without payment

## Module history

- `17.4`
  - The support for tokenization via `Card` is added. odoo/odoo#158445
- `17.0`
  - The first version of the module is merged. odoo/odoo#141661

## Testing instructions

https://developers.xendit.co/api-reference/#test-scenarios

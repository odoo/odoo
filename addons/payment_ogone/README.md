# Ogone

## Technical details

APIs:

- [Hosted Payment Page](https://support.legacy.worldline-solutions.com/integration-solutions/integrations/hosted-payment-page?com.dotmarketing.htmlpage.language=1&skiprules=true&com.dotmarketing.htmlpage.language=1&skiprules=true)
- [Direct Link](https://support.legacy.worldline-solutions.com/integration-solutions/integrations/directlink?com.dotmarketing.htmlpage.language=1&skiprules=true&com.dotmarketing.htmlpage.language=1&skiprules=true)

This module relies on a combination of two APIs to implement a payment with redirection flow that
allows for tokenization. The Hosted Payment Page API is integrated using the generic payment with
redirection flow based on form submission provided by the `payment` module. The Direct Link API
is used for token payments.

## Supported features

- Payment with redirection flow
- Webhook notifications
- Tokenization with payment

## Not implemented features

- Tokenization without payment

## Module history

- `14.3`
  - The FlexCheckout API is removed and with it the support for payment method validations.
    odoo/odoo#72624
  - The FlexCheckout API is introduced to handle payment method validations that were performed in
    a non-secure way through the Hosted Payment Page API. odoo/odoo#56187
  - The module is renamed from `payment_ingenico` to `payment_ogone`. odoo/odoo#56187

## Testing instructions

Test card numbers are specific to the Ogone account. From Ogone's Backoffice, find them in
Configuration > Technical information > Test info.

# Paymob

## Technical details

API: [Paymob API Checkout](https://developers.paymob.com/egypt/api-reference-guide)

API Backend: [Paymob Internal Odoo APIs](https://www.odoo.com/odoo/project/4106/tasks/4196623)

This module required two integrations from Paymob. The backend API allows to modify payment methods
on their portal to set callback URLs and indicate which ones are enabled on Odoo.

As initial setup, user must click on synchronize payment methods buttons to synchronize between
payment methods of paymob and Odoo

This module follows the generic payment with redirection flow based on form submission provided by
the `payment` module.

## Supported features

- Redirect payment flow
- Webhook notifications

## Module history

- `18.4`
  - The first version of the module is merged. odoo/odoo#193107

## Testing instructions

Paymob redirects to a payment page with possibility to simulate payments and select different
possible outcomes after filling the information required based on selected payment method.

# PayUmoney

## Technical details

API: [PayUMoney Payment Gateway](https://www.payumoney.com/pdf/PayUMoney-Technical-Integration-Document.pdf)

This module integrates PayUmoney using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow

## Module history

- `16.0`
  - The module is deprecated and can no longer be installed from the web client. odoo/odoo#99025
- `15.2`
  - The signature of synchronous notifications (redirect payloads) is verified. odoo/odoo#81607

## Testing instructions

**Phone**: `123456`

**Email**: `test@example.com`

**Card Number**: `4012001037141112`

**Expiry**: any date in the future

**CVV**: `123`

**TOTP**: `123456`
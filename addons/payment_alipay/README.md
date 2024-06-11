# Alipay

## Technical details

API: [Global API](https://global.alipay.com/docs/ac/global/create_forex_trade) that is part of the
[cross-border website payment solution](https://global.alipay.com/docs/ac/web/integration)

This module integrates Alipay using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications

## Module history

- `17.0`
  - The support for customer fees is removed as it is no longer supported by the `payment` module.
    odoo/odoo#132104
- `16.0`
  - The module is deprecated and can no longer be installed from the web client. odoo/odoo#99025
- `15.2`
  - Webhook notifications that cannot be processed are discarded to prevent automatic disabling of
    the webhook. odoo/odoo#81607

## Testing instructions

https://docs.smart2pay.com/s2p_testdata_24/

**Buyer Account**: `cnbuyer_8292@alitest.com`

**Login password**: `111111`

**Payment password**: `111111`

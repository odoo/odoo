# SIPS

## Technical details

API: [SIPS Paypage](https://docs.sips.worldline-solutions.com/en/WLSIPS.317-UG-Sips-Paypage-POST.html#Data-field-element-syntax_)

<!-- https://documentation.sips.worldline.com/en/WLSIPS.316-UG-Sips-Paypage-JSON.html = 404 -->

This module integrates SIPS using the generic payment with redirection flow based on form
submission provided by the `payment` module.

## Supported features

- Payment with redirection flow
- Webhook notifications

## Module history

- `15.2`
  - An HTTP 404 "Forbidden" error is raised instead of a Validation error when the authenticity of
    the webhook notification cannot be verified. odoo/odoo#81607

## Testing instructions

### VISA

**Card Number**: `4100000000000000`

### MasterCard

**Card Number**: `5100000000000000`
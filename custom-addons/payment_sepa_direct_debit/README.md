# Sepa Direct Debit

## Technical details

This module does not integrate with an API and, instead, allows to create SEPA Direct Debit mandates
from a custom payment form on the payment page. Mandates are linked to payment tokens; when used to
make a payment, they create `account.payment` records that must be sent to a bank to collect the
payment.

## Supported features

- Direct payment flow
- Tokenization with our without payment

## Module history

- `16.4`
  - An initial wire transfer is required to confirm the SEPA mandate; subsequent payments are
    immediately confirmed. odoo/enterprise#43418
- `16.1`
  - SEPA Direct Debit is restricted to the EUR currency. odoo/enterprise#34158
- `16.0`
  - The payment form is revamped. odoo/enterprise#30652
  - Transactions are immediately confirmed. odoo/enterprise#27251

## Testing instructions

SEPA Direct Debit doesn't have a test mode.

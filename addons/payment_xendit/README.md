# Xendit

## Implementation details

### Supported features

- [Payment with redirection flow](https://developers.xendit.co/api-reference/#create-invoice)
- Several payment methods such as credit cards, bank transfers, eWallets, pay later, and
  [others](https://docs.xendit.co/payment-link/payment-channels).
- [Webhook](https://developers.xendit.co/api-reference/#invoice-callback).

In addition, Xendit also allows to implement tokenization.

### API and gateway

We choose to integrate with the
[Invoices API](https://developer.flutterwave.com/docs/collecting-payments/standard/) as it
is the gateway that covers the best our needs: it is a payment with redirection flow and is
compatible with `payment`'s form-based implementation of that flow.

The [Payments API](https://developers.xendit.co/api-reference/#payments-api) was considered too, but
it requires implementing a more complex direct payment flow and linking the customer account. 

The version of the API implemented by this module is v2.

## Merge details

The first version of the module was specified in task
[2946329](https://www.odoo.com/web#id=2759117&model=project.task) and merged with PR
odoo/odoo#141661 in branch `17.0`.

## Testing instructions

https://developers.xendit.co/api-reference/#test-scenarios
# Flutterwave

## Implementation details

### Supported features

- Payment with redirection flow
- [Tokenization](https://developer.flutterwave.com/reference/endpoints/tokenized-charge/)
- Several payment methods such as credit cards, M-Pesa, and
  [others](https://developer.flutterwave.com/docs/collecting-payments/payment-methods/).
- [Webhook](https://developer.flutterwave.com/docs/integration-guides/webhooks/).

In addition, Flutterwave also allows to implement refunds and pre-authorizations.

### API and gateway

We choose to integrate with
[Flutterwave standard](https://developer.flutterwave.com/docs/collecting-payments/standard/) as it
is the gateway that covers the best our needs, out of the three that Flutterwave offers as of
May 2022. See the task's dev notes for the details on the other gateways.

The version of the API implemented by this module is v3.

## Merge details

The first version of the module was specified in task
[2759117](https://www.odoo.com/web#id=2759117&model=project.task) and merged with PR
odoo/odoo#84820 in `saas-15.4`.

## Testing instructions

https://developer.flutterwave.com/docs/integration-guides/testing-helpers
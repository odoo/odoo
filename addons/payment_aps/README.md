# Amazon payment Services

## Implementation details

### Supported features

- Payment with redirection flow
- Payment by several global and local credit
  [cards](https://paymentservices.amazon.com/docs/EN/24a.html).
- [Webhook](https://paymentservices-reference.payfort.com/docs/api/build/index.html#transaction-feedback)

### API and gateway

We choose to integrate with the
[Redirection](https://paymentservices-reference.payfort.com/docs/api/build/index.html#redirection)
API as it is the gateway that covers the best our needs, out of the three that Amazon Payment
Services offers as of July 2022. See the task's dev notes for the details on the other gateways.

## Merge details

The first version of the module was specified in task
[2802678](https://www.odoo.com/web#id=2802678&model=project.task) and merged with PR odoo/odoo#95860
in `saas-15.5`.

## Testing instructions

https://paymentservices.amazon.com/docs/EN/12.html
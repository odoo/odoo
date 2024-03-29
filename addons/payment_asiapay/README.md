# AsiaPay

## Implementation details

### Supported features

- Payment with redirection flow.
- Webhook.
- Several payment methods including credit cards, chinese payment methods such as Alipay, and 
  [others](https://www.asiapay.com/payment.html#option).

In addition, AsiaPay also allows to implement manual capture, refunds, express checkout, and
multi-currency processing.

### API and gateway

We choose to integrate with the Client Post Through Browser gateway which covers the best our needs,
out of the three that AsiaPay offers as of August 2022.

The entire API reference and the integration guides can be found on the [Integration Guide]
(https://www.paydollar.com/pdf/op/enpdintguide.pdf).

The version of the API implemented by this module is v3.67.

## Merge details

The first version of the module was specified in task
[2845428](https://www.odoo.com/web#id=2845428&model=project.task) and merged with PR
odoo/odoo#98441 in `saas-15.5`.

## Testing instructions

Card Number: `4335900000140045`
Expiry Date: `07/2030`
Name: `testing card`
CVC: `123`
3DS Password: `password`

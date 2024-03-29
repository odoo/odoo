# Mercado Pago

## Implementation details

### Supported features

- Payment with redirection flow
- Several payment methods such as credit cards, debit cards, and
  [others](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-methods/other-payment-methods).
- [Webhook](https://www.mercadopago.com.mx/developers/en/docs/notifications/webhooks/webhooks)
  notifications.

### Not implemented features

- [Manual capture](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-management/capture-authorized-payment).
- [Partial refunds](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/payment-management/cancellations-and-refunds).

### API and gateway

We choose to integrate with a combination of the
[Checkout Pro](https://www.mercadopago.com.mx/developers/en/docs/checkout-pro/landing) and
[Checkout API](https://www.mercadopago.com.mx/developers/en/docs/checkout-api/landing) solutions:
The payment with redirection flow is initiated by sending a client HTTP request with a form-encoded
payload like Checkout Pro's JavaScript SDK does under the hood. The remaining API calls are made
according to the Checkout API's documentation. It was not possible to integrate with Checkout Pro
only as it only allows redirecting customers to the payment page, nor with the Checkout API only as
it requires building a custom payment form to accept direct payments from the merchant's website.

The other gateways were ruled out. See the task's dev notes for the details on the other gateways.

The API implemented by this module is not versioned.

## Merge details

The first version of the module was specified in task
[2704764](https://www.odoo.com/web#id=2704764&model=project.task) and merged with PR
odoo/odoo#83957 in `saas-15.5`.

## Testing instructions

https://www.mercadopago.com.mx/developers/en/docs/checkout-api/integration-test/test-cards

# Razorpay

## Implementation details

### Supported features

- Direct payment flow
- Tokenization
- Manual capture
- Partial refunds
- Several payment methods such as debit/credit cards, netbanking, UPI, and
  [others](https://razorpay.com/docs/payments/payment-methods/).
- [Webhook](https://razorpay.com/docs/webhooks).

### API and gateway

We choose to integrate with
[Razorpay Recurring Payments](https://razorpay.com/docs/api/payments/recurring-payments/), which is
more complex to handle than
[Razorpay Hosted Checkout](https://razorpay.com/docs/payments/payment-gateway/web-integration/hosted)
because it works as a direct payment flow, because it allows for tokenization. The other gateways
were ruled out; see the original task's dev notes for the details on the other gateways.

The version of the API implemented by this module is v1.

## Module history

- The first version of the module was specified in task
  [2800823](https://www.odoo.com/web#id=2800823&model=project.task) and merged with PR
  odoo/odoo#92848 in `saas-15.5`.
- The API was changed to the Recurring Payments API to support tokenization with PR odoo/odoo#143525
  in `17.0`.

## Testing instructions

- The partner's phone number must be a valid Indian phone number. Example: +911234567890
- The partner's country must be India and the payment currency INR to enable India-based payment
  methods.

See https://razorpay.com/docs/payments/payments/test-card-upi-details/ and
https://razorpay.com/docs/payments/payments/test-upi-details/ for the list of test payment details.

# Razorpay

## Implementation details

### Supported features

- Payment with redirection flow
- Manual capture
- Partial refunds
- Several payment methods such as debit/credit cards, netbanking, UPI, and
  [others](https://razorpay.com/docs/payments/payment-methods/).
- [Webhook](https://razorpay.com/docs/webhooks).

In addition, Razorpay also allows to implement tokenization but requires passing the card secret for
each transaction.

### API and gateway

We choose to integrate with
[Razorpay Hosted Checkout](https://razorpay.com/docs/payments/payment-gateway/web-integration/hosted).
The other gateways were ruled out. See the task's dev notes for the details on the other gateways.

The version of the API implemented by this module is v1.

## Merge details

The first version of the module was specified in task
[2800823](https://www.odoo.com/web#id=2800823&model=project.task) and merged with PR
odoo/odoo#92848 in `saas-15.5`.

## Testing instructions

The partner's phone number must be a valid Indian phone number. Example: +91123456789

See https://razorpay.com/docs/payments/payments/test-card-upi-details/ for the list of test
payment details.

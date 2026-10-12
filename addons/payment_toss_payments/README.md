# Toss Payments

## Technical details

SDK: Toss Payments JavaScript SDK (Version 2)

APIs (Version 2024-06-01):

- [Payment APIs](https://docs.tosspayments.com/en/api-guide)
- [Webhook events](https://docs.tosspayments.com/en/webhooks)

This module relies on the Toss Payments JavaScript SDK, loaded from
`https://js.tosspayments.com/v2/standard`, to open the Toss-hosted payment window and collect the
payment details in a secure way.

For the front-end, the `PaymentForm` component is patched to:

- Force the **direct** payment flow when a Toss Payments option is selected.
- Load the Toss Payments SDK dynamically.
- Open the Toss payment window in a modal with the transaction data (amount, order reference,
  customer information, and success/failure return URLs).

On the backend, after the customer completes the payment on Toss Payments and is redirected back to
Odoo on the success URL, a server-to-server API call is made to the
`/v1/payments/confirm` endpoint to confirm the payment. The response is then processed to update the
transaction state and store the `paymentKey` and `secret` fields returned by Toss Payments.

Webhook notifications are used to keep the transaction state in sync with Toss Payments:

- The webhook endpoint receives `PAYMENT_STATUS_CHANGED` events.
- The payload is matched to an Odoo transaction by reference (`orderId`).
- A signature-like check is performed by comparing the `secret` in the event with the one
  stored on the transaction when the payment was confirmed.
- If the verification passes, the transaction is processed and its state updated according to the
  Toss Payments status.

## Supported features

- Direct payment flow using the Toss-hosted payment window
- Webhook notifications for payment status changes
- Basic Authentication with secret keys for API calls
- Support for the following payment methods (via default payment method codes):
  - Card
  - Bank transfer
  - Mobile phone payments
- Single-currency support for `KRW`

## Not implemented features

- Tokenization or saving payment methods
- Refunds initiated from Odoo
- Express checkout
- Less common payment methods: virtual account, gift certificates, and overseas payment

## Testing instructions

**Checklist**
- Change company location to South Korea and currency to KRW.
- Activate payment provider and payment methods. Client key and secret key are available at
  credentials page.
- Register 'PAYMENT_STATUS_CHANGE' webhook on Toss Payments developer portal. If you're testing
  locally, you need to setup tools like [ngrok](https://ngrok.com/) to expose the local server.

**Procedure**
1. Confirm an invoice and generate payment link (the gear icon).
2. Open the payment link in incognito browser.
3. Test different payment methods.

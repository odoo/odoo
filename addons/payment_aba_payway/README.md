# ABA PayWay

## Technical details

API: [eCommerce Checkout API](https://developer.payway.com.kh/ecommerce-checkout-3158159f0)
version `1`

This module integrates ABA PayWay using the redirect payment flow. When the customer proceeds with
the payment, the signed purchase request is posted to ABA PayWay, which displays its hosted
checkout, pre-selected on the payment method chosen in Odoo. No payment details are collected on
the Odoo payment form.

The purchase request is signed with HMAC-SHA512 using the merchant's API key. Once the payment is
completed, ABA PayWay sends a webhook notification to the `return_url` of the purchase request. The
notification includes the payment details (original amount and currency, payment type, approval
code...), and its signature (HMAC-SHA512 over all the values sorted by key) is included in the
`X-PayWay-HMAC-SHA512` header. The payment data are processed directly from the notification,
without any additional API request.

As webhook notifications are only sent to whitelisted domains and their delivery is not
guaranteed, the customer is redirected to a return route (the `continue_success_url` of the purchase
request) after a successful payment, where the status of the transaction is fetched with the
[Check transaction API](https://developer.payway.com.kh/check-transaction-14530826e0), unless the
webhook notification was already received.

ABA PayWay never reports unpaid transactions as failed: no webhook notification is sent for declined
payments, and declined or expired transactions keep the pending status (`2`). The hosted checkout
offers no way to cancel the payment and never redirects the customer back after a declined or
expired payment, so abandoned transactions remain in draft.

## Supported features

- Redirect payment flow
- Webhook notifications
- Multiple payment methods:
  - ABA KHQR (ABA Pay and other KHQR member banks)
  - Credit/debit card (Visa, Mastercard, JCB, UnionPay)
  - Alipay
  - WeChat Pay
- Multi-currency support for `KHR` and `USD`

## Not implemented features

- Google Pay
- Manual capture
- Refunds
- Tokenization

## Testing instructions

https://developer.payway.com.kh/ecommerce-checkout-3158159f0

Sandbox credentials are sent by email after registering on
https://sandbox.payway.com.kh/register-sandbox/. The domain of the Odoo instance must be
whitelisted in the merchant profile for the webhook notifications to be sent.

Test cards: https://developer.payway.com.kh/resources-3305682f0

- Successful payment: `5156 8399 3770 6777`, expiry `01/30`, CVV `993`
- Declined payment: `4156 8399 3770 6777`, expiry `01/30`, CVV `993`

Alipay and WeChat Pay must be enabled on the merchant profile, or ABA PayWay rejects the purchase
request with the error code `23`.

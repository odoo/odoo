# ABA PayWay

## Technical details

API: [eCommerce Checkout API](https://developer.payway.com.kh/ecommerce-checkout-3158159f0)
version `1`

SDK: [PayWay checkout plugin](https://checkout.payway.com.kh/plugins/checkout2-0.js)

This module integrates ABA PayWay using the direct payment flow. When the customer proceeds with
the payment, the PayWay checkout SDK opens the checkout hosted by ABA PayWay in a modal, pre-selected
on the payment method chosen in Odoo. No payment details are collected on the Odoo payment form.

The purchase request is signed with HMAC-SHA512 using the merchant's API key. Once the payment is
completed, ABA PayWay sends a webhook notification to the `return_url` of the purchase request. The
notification includes the payment details (original amount and currency, payment type, approval
code...), and its signature (HMAC-SHA512 over all the values sorted by key) is included in the
`X-PayWay-HMAC-SHA512` header. The payment data are processed directly from the notification,
without any additional API request.

## Supported features

- Direct payment flow
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

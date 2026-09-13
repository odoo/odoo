# QFPay

## Technical details

API: QFPay OpenAPI version `v1`

Integration
guide: [QFPay Payment Element](https://sdk.qfapi.com/integration/online-shop/checkout-integration/payment-element)

This module integrates QFPay using a direct payment flow based on the QFPay Element SDK.

When a payment method is selected, the frontend loads the QFPay SDK dynamically and stores the
provider environment values required to initialize the checkout session.

When the payment is submitted, a server-to-server API call is made to create a payment intent on
QFPay's side.

Because QFPay requires its wallet element to be rendered outside the HTML form, the SDK renders the
wallet picker inside an Odoo dialog before confirming the payment. The return URL then triggers a
transaction query to reconcile the final status if the transaction is not already finalized.

Webhook notifications are supported and their authenticity is verified with the `X-QF-SIGN`
signature header before the transaction is processed.

The provider requires an `App Code` and an `App Key`.

## Supported features

- Direct payment flow
- Webhook notifications
- Multiple payment methods:
    - Alipay
    - Alipay HK
    - WeChat Pay
    - UnionPay
    - FPS
    - PayMe
    - Card payments (Visa, Mastercard, JCB, UnionPay)
    - Multi-currency support for `HKD`, `CNY`, `USD`, `AED`, `EUR`, `IDR`, `JPY`, `MMK`, `MYR`, `SGD`, `THB`, `CAD`, and
      `AUD`

## Not implemented features

- Tokenization
- Manual capture
- Refunds
- Express checkout

## Module history

- `20.0`
    - The first version of the module is merged. odoo/odoo#262954

## Testing instructions

Set the provider to test mode and configure the QFPay test credentials (`App Code` and `App Key`).

Note that QFPay provides three environments: `sandbox`, `live testing`, and `production`.

Odoo's `test` mode in configured to use the `sandbox` environment, which is used for development and testing with simulated transactions.
However, the `sandbox` environment only supports Card payments ([Test cards](https://sdk.qfapi.com/integration/online-shop/integration-by-payment-type/visa-master-online-payment#test-cards)).

For more information, see
the [QFPay Payment Element](https://sdk.qfapi.com/integration/online-shop/checkout-integration/payment-element).

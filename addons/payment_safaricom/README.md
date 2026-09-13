# Safaricom M-Pesa

## Technical details

APIs:
- [Authorization](https://developer.safaricom.co.ke/apis/Authorization) version `1`
- [M-Pesa Express](https://developer.safaricom.co.ke/apis/MpesaExpressSimulate) version `1`

This module integrates Safaricom M-Pesa using a direct payment flow based on the M-Pesa express API. When a customer initiates a payment, an STK Push prompt is sent to their mobile
phone asking them to confirm the transaction by entering their M-Pesa PIN. Safaricom then notifies
Odoo of the payment result via a signed webhook callback.

Both **PayBill** and **BuyGoods (Till)** transaction types are supported and can be configured on
the provider.

## Supported features

- Direct payment flow
- Webhook notifications

## Not implemented features

- [Refunds](https://developer.safaricom.co.ke/apis/Reversal)
- [Manual Reconciliation](https://developer.safaricom.co.ke/apis/MpesaExpressQuery)

## Module history

- `20.0`
  - The first version of the module is merged. odoo/odoo#268897

## Testing instructions

**Shortcode**: `174379`
**Phone number**: `254708374149`

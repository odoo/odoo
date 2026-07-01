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

- Direct payment flow (STK Push)
- Webhook notifications
- PayBill and BuyGoods (Till) transaction types

## Not implemented features

- [Refunds](https://developer.safaricom.co.ke/apis/Reversal)
- [Manual Reconciliation](https://developer.safaricom.co.ke/apis/MpesaExpressQuery)
- [C2B Payments](https://developer.safaricom.co.ke/apis/CustomerToBusiness)
- [QR Code Payments](https://developer.safaricom.co.ke/apis/DynamicQRCode)

## Module history

- `19.4`
  - The first version of the module is merged. odoo/odoo#268897

## Testing instructions

**Consumer key**: `WIE6GXsAoGDa4AZ8AsVFq06NSQZwyTZB85y7xjj9Nij6Rom6`
**Consumer secret**: `Yh9GpjTcrPj2L2v8Bo9PFOlGEAk5SWKMqQiMVGN9pTDJfMxtyZfvkxGy4Vj11cls`
**Passkey**: `bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919`
**Shortcode**: `174379`
**Phone number**: `254708374149`

# Payment Ecpay

- Payment Acquirer: Ecpay Implementation

## Configure

- Change state to `Enabled`
- Setup ecpay credentials
    - Merchant Partner ID
    - HashKey
    - HashIV
## Local Testing

- Command line to export localhost to public since Ecpay need to redirect to a public link
    - `ngrok http 8069`
    - Open the link from ngrok
-  Change state to `Test Mode`
-  Setup ecpay testing credentials
    -  Merchant Partner ID = 2000214
    -  HashKey = 5294y06JbISpM5x9
    -  HashIV = v77hoKGq4kWxNNIS
- Testing credit card: 4311-9522-2222-2222

## Ecpay Reference

- API Documentation - [Link](https://www.ecpay.com.tw/Content/files/ecpay_011.pdf)
- SDK - [Link](https://github.com/ECPay/ECPayAIO_Python)

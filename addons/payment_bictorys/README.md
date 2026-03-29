# Payment Provider: Bictorys

## Overview

Bictorys is a West African payment provider supporting online (e-commerce) and
Point of Sale payments. This module integrates Bictorys into Odoo's native
payment framework (`payment` module) and the Odoo Point of Sale (`point_of_sale`
module).

### Features

- **Online payments** (eCommerce / website): redirect flow to the Bictorys-hosted
  payment page.
- **Point of Sale payments**: optional Bictorys terminal payment method per POS
  configuration, with real-time status polling via webhook.

### Supported currencies

- XOF (West African CFA franc)
- XAF (Central African CFA franc)
- GNF (Guinean franc)
- USD, EUR

---

## Configuration

### 1. Online Payments

1. Go to **Accounting → Configuration → Payment Providers**.
2. Activate **Bictorys** and enter your **Secret Key** and **Webhook Secret**.
3. Set the provider state to **Test** or **Production**.
4. Configure the webhook URL on the Bictorys platform:
   `https://<your-domain>/payment/bictorys/webhook`

### 2. Point of Sale Payments

The Bictorys POS payment method is **optional** and must be explicitly enabled
per POS configuration:

1. Go to **Point of Sale → Configuration → Point of Sale**.
2. Open the POS configuration you want to enable Bictorys for.
3. In the **Bictorys** section, select the **POS Payment Method** linked to your
   Bictorys terminal.
4. Configure the POS webhook URL on the Bictorys platform:
   `https://<your-domain>/payment/bictorys/pos/webhook`

> **Note:** If no Bictorys payment method is selected in a POS configuration,
> Bictorys is completely disabled for that POS.

---

## Webhook Setup

### Online Payments Webhook

| Field | Value |
|---|---|
| URL | `https://<your-domain>/payment/bictorys/webhook` |
| Method | `POST` |
| Auth Header | `X-Secret-Key: <your webhook secret>` |

### POS Payments Webhook

| Field | Value |
|---|---|
| URL | `https://<your-domain>/payment/bictorys/pos/webhook` |
| Method | `POST` |
| Auth Header | `X-Secret-Key: <your webhook secret>` |

---

## Module Structure

```
payment_bictorys/
├── controllers/
│   └── main.py              # HTTP routes: return URL, online webhook, POS webhook
├── data/
│   ├── neutralize.sql       # Clears credentials in neutralized databases
│   └── payment_provider_data.xml
├── models/
│   ├── payment_provider.py  # payment.provider inherit
│   ├── payment_transaction.py  # payment.transaction inherit
│   ├── pos_config.py        # pos.config inherit (optional bictorys_payment_method_id)
│   └── pos_order.py         # pos.order inherit (Bictorys order creation & status)
├── static/src/
│   ├── css/bictorys_pos.css
│   ├── js/
│   │   ├── payment_form.js          # Frontend (eCommerce) override
│   │   └── bictorys_payment_method.js  # POS payment screen patch
│   └── xml/bictorys_payment_method.xml  # OWL dialog templates
├── tests/
│   ├── common.py
│   └── test_bictorys.py
├── views/
│   ├── payment_provider_views.xml
│   ├── payment_transaction_views.xml
│   └── pos_config_views.xml
├── const.py
├── __init__.py
└── __manifest__.py
```

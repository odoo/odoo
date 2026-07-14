# Baiwang API Reference (Validated Against Sandbox)

> **Validated:** 2026-05-21
> **Sandbox Endpoint:** `https://sandbox-openapi.baiwang.com/router/rest`
> **Production Endpoint:** `https://openapi.baiwang.com/router/rest`
> **Reference Script:** `baiwang_test.py` (all endpoints validated)

---

## 1. Authentication (`baiwang.oauth.token`)

### Key Facts
- **No signature required** for this endpoint
- URL query params carry routing info; JSON body carries credentials
- Token is valid ~8 hours; refresh token valid 30 days

### Request

```
POST /router/rest?method=baiwang.oauth.token&grant_type=password&client_id={appKey}&version=7.0&timestamp={ms}&encryptType=NONE&encryptScope=00

Body (JSON):
{
  "password": "<SHA256(plaintext_password + salt)>",
  "username": "<username>",
  "client_secret": "<appSecret>"
}
```

### Password Hashing
```python
password_hash = SHA256(plain_password + user_salt)  # lowercase hex string
```

### Key Notes
- `orgAuthCode` is **only required for 3rd-party apps**. If appKey belongs to an internal enterprise app, omit it.
- In `baiwang_test.py`, the auth call uses `requests.post(json=body)` (NOT compact JSON) and works.

---

## 2. Signature Formula (All Business APIs)

All business API calls (everything except `baiwang.oauth.token`) use MD5 signing:

```
sign = MD5(appSecret + sorted_url_params_concatenated + raw_body_json + appSecret).upper()
```

### Step by Step

1. Take all URL query params (excluding `sign` itself)
2. Sort keys alphabetically
3. Concatenate: `key1value1key2value2...` (skip keys with empty/null values)
4. Build string: `appSecret` + concatenated_params + `compact_json_body` + `appSecret`
5. MD5 hash → uppercase hex

### Critical Details

- **Body JSON must be compact** (no spaces): `json.dumps(body, separators=(',', ':'))`
- The **entire body** is included in the sign, not just the `data` field
- Send body as `data=body_str.encode('utf-8')` with `Content-Type: application/json; charset=utf-8`
- Do NOT use `requests.post(json=...)` for business APIs — it adds spaces that break the signature

---

## 3. API Body Patterns

### Pattern A: v6.0 with `data` wrapper
**Used by:** `invoice.issue`, `terminal.query`

```
URL: ?method=...&version=6.0&appKey=...&format=json&timestamp=...&token=...&type=sync&requestId=...&sign=...

Body:
{
  "taxNo": "...",
  "data": {
    // business content here
  }
}
```

### Pattern B: v7.0 flat body
**Used by:** `redinvoice.add`, `redinvoice.operate`, `redinvoice.formlist`

```
URL: ?method=...&version=7.0&appKey=...&format=json&timestamp=...&token=...&type=sync&requestId=...&signType=MD5&encryptType=NONE&encryptScope=00&sign=...

Body:
{
  "taxNo": "...",
  "field1": "...",
  "field2": "...",
  // ALL fields flat at top level, no "data" wrapper
}
```

### Pattern C: v6.0 flat body (no `data` wrapper, no extra v7 URL params)
**Used by:** `redinvoice.redforminfo`

```
URL: ?method=...&version=6.0&appKey=...&format=json&timestamp=...&token=...&type=sync&requestId=...&sign=...

Body:
{
  "taxNo": "...",
  "sellerTaxNo": "...",
  "redConfirmUuid": "...",
  // flat, no "data" wrapper
}
```

### How to Tell Which Pattern
- Check the docs' `version` field (6.0 vs 7.0)
- Check if docs show `signType`/`encryptType`/`encryptScope` in public params → v7.0
- Check the request example's body structure (has `"data":{}` or not)

---

## 4. Invoice Issue (`baiwang.output.invoice.issue`)

**Pattern:** A (v6.0 + data wrapper)

### Minimal Working Request
```json
{
  "taxNo": "DB20240220YHCS1009",
  "data": {
    "invoiceType": "0",
    "invoiceTypeCode": "02",
    "priceTaxMark": "0",
    "invoiceListMark": "0",
    "taxationMethod": "0",
    "serialNo": "UNIQUE_SERIAL",
    "buyerName": "Buyer Co",
    "buyerTaxNo": "91110108MA01KPGP0L",
    "invoiceTotalPrice": 2.0,
    "invoiceTotalTax": 0.2,
    "invoiceTotalPriceTax": 2.2,
    "invoiceDetailsList": [{
      "goodsLineNo": 1,
      "invoiceLineNature": "0",
      "goodsCode": "1010101070000000000",
      "goodsName": "燕麦",
      "goodsTaxRate": 0.1,
      "goodsTotalPrice": 2.0,
      "goodsTotalTax": 0.2,
      "preferentialMarkFlag": "0"
    }]
  }
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `invoiceType` | String | ✅ | `"0"` = blue (positive), `"1"` = red (negative) |
| `invoiceTypeCode` | String | ✅ | `"01"` = special, `"02"` = general |
| `priceTaxMark` | String | ✅ | `"0"` = prices exclude tax, `"1"` = include |
| `invoiceListMark` | String | ✅ | `"0"` = no list, `"1"` = has list attachment |
| `taxationMethod` | String | ✅ | `"0"` = general, `"1"` = simplified |
| `serialNo` | String | ✅ | Unique per request (idempotency key) |
| `buyerName` | String | ✅ | Buyer company name |
| `buyerTaxNo` | String | ✅ | Buyer tax registration number |
| `invoiceTotalPrice` | Number | ✅ | Sum of all line prices (tax-exclusive) |
| `invoiceTotalTax` | Number | ✅ | Sum of all line taxes |
| `invoiceTotalPriceTax` | Number | ✅ | Total including tax |
| `buyerAddress` | String | | Buyer address |
| `buyerPhone` | String | | Buyer phone |

### Line Item Fields (`invoiceDetailsList[]`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `goodsLineNo` | Integer | ✅ | Line sequence number (1-based) |
| `invoiceLineNature` | String | ✅ | `"0"` = normal, `"1"` = discount, `"2"` = deducted |
| `goodsCode` | String | ✅ | 19-digit tax category code |
| `goodsName` | String | ✅ | Product name |
| `goodsTaxRate` | Number | ✅ | Decimal tax rate (0.13, 0.09, 0.06, 0.03, etc.) |
| `goodsTotalPrice` | Number | ✅ | Line total (tax-exclusive) |
| `goodsTotalTax` | Number | ✅ | Line tax amount |
| `preferentialMarkFlag` | String | ✅ | `"0"` = no preferential policy |
| `goodsQuantity` | String | | Quantity |
| `goodsPrice` | String | | Unit price |
| `goodsUnit` | String | | Unit of measure |

### Response

```json
{
  "success": true,
  "response": {
    "success": [{
      "invoiceNo": "24442000000071309399",
      "invoiceDate": "20260521152632",
      "invoiceQrCode": "...",
      "invoiceDetailsList": [{
        "goodsName": "*谷物*燕麦"
      }]
    }],
    "fail": []
  }
}
```

- `invoiceNo`: 20-digit number for 全电 invoices
- `invoiceDate`: Format `YYYYMMDDHHmmss`
- `goodsName` in response gets prefixed with tax category (e.g. `*谷物*燕麦`)

---

## 5. Red Invoice Workflow

### Complete Flow
```
Blue Invoice (issue) → Red Confirmation (add) → [Poll/Query status] → [Operate: confirm/deny/revoke]
                                                                              ↓
                                                                    Red invoice auto-issued on confirm
```

### 5.1 Red Confirmation Add (`baiwang.output.redinvoice.add`)

**Pattern:** B (v7.0 flat)

#### Confirm States
| Code | Meaning |
|------|---------|
| `01` | No confirmation needed (auto-approved) |
| `02` | Seller entered, waiting for buyer |
| `03` | Buyer entered, waiting for seller |
| `04` | Both confirmed |
| `05`-`10` | Various rejection/cancellation states |

#### Request Body (flat, no `data` wrapper)
```json
{
  "taxNo": "DB20240220YHCS1009",
  "redConfirmSerialNo": "RED_1716285600",
  "entryIdentity": "01",
  "sellerTaxNo": "DB20240220YHCS1009",
  "sellerTaxName": "Seller Company",
  "buyerTaxName": "Buyer Company",
  "buyerTaxNo": "91110108MA01KPGP0L",
  "originInvoiceIsPaper": "N",
  "originalInvoiceNo": "24442000000071309399",
  "originInvoiceDate": "2026-05-21 15:26:32",
  "originInvoiceTotalPrice": 2.0,
  "originInvoiceTotalTax": 0.2,
  "originInvoiceType": "02",
  "invoiceTotalPrice": -2.0,
  "invoiceTotalTax": -0.2,
  "redInvoiceLabel": "01",
  "invoiceSource": "2",
  "priceTaxMark": "0",
  "autoIssueSwitch": "Y",
  "deliverFlag": "0",
  "redInvoiceIsPaper": "N",
  "redConfirmDetailReqEntityList": [{
    "originalInvoiceDetailNo": 1,
    "goodsLineNo": 1,
    "goodsCode": "1010101070000000000",
    "goodsName": "*谷物*燕麦",
    "goodsSimpleName": "谷物",
    "projectName": "燕麦",
    "goodsTaxRate": 0.1,
    "goodsTotalPrice": -2.0,
    "goodsTotalTax": -0.2,
    "goodsQuantity": "-1",
    "goodsPrice": "2.0",
    "goodsUnit": "份"
  }],
  "originalPaperInvoiceCode": "",
  "originalPaperInvoiceNo": "",
  "orgCode": "",
  "accessPlatformNo": "",
  "taxUserName": "",
  "drawer": "",
  "drawerCredentialsType": "",
  "drawerCredentialsNo": "",
  "buyerEmail": "",
  "buyerPhone": "",
  "originInvoiceSetCode": "",
  "ext": {}
}
```

#### Key Fields

| Field | Values | Description |
|-------|--------|-------------|
| `entryIdentity` | `"01"` = seller, `"02"` = buyer | Who is entering the red form |
| `invoiceSource` | `"1"` = old tax system, `"2"` = digital platform | Source system |
| `originInvoiceType` | `"01"` = 专票, `"02"` = 普票 | Type of original invoice |
| `redInvoiceLabel` | `"01"`-`"04"` | Reason code (see PLAN.md §4) |
| `autoIssueSwitch` | `"Y"` / `"N"` | Auto-issue red invoice on confirmation |

#### Response
```json
{
  "success": true,
  "response": [{
    "redConfirmUuid": "uuid-string",
    "redConfirmNo": "confirmation-number",
    "confirmState": "01"
  }]
}
```

---

### 5.2 Red Form Operate (`baiwang.output.redinvoice.operate`)

**Pattern:** B (v7.0 flat)

```json
{
  "taxNo": "DB20240220YHCS1009",
  "sellerTaxNo": "DB20240220YHCS1009",
  "redConfirmUuid": "uuid-from-add-response",
  "redConfirmNo": "confirm-number",
  "confirmType": "03",
  "taxUserName": ""
}
```

| `confirmType` | Action |
|---------------|--------|
| `"01"` | Confirm (agree) |
| `"02"` | Deny (reject) |
| `"03"` | Revoke (cancel) |

After revoke: `confirmState` becomes `"08"` (发起方已撤销)

---

### 5.3 Red Form List (`baiwang.output.redinvoice.formlist`)

**Pattern:** B (v7.0 flat)

```json
{
  "taxNo": "DB20240220YHCS1009",
  "sellerTaxNo": "DB20240220YHCS1009",
  "buySelSelector": "0",
  "entryIdentity": "01",
  "pageNo": 1,
  "pageSize": 50,
  "queryAll": true,
  "invoiceStartDate": "2026-05-21",
  "invoiceEndDate": "2026-05-22"
}
```

| Field | Description |
|-------|-------------|
| `buySelSelector` | `"0"` = querying as seller, `"1"` = as buyer |
| `pageSize` | Max 50 |

---

### 5.4 Red Form Detail (`baiwang.output.redinvoice.redforminfo`)

**Pattern:** C (v6.0 flat, no data wrapper)

```json
{
  "taxNo": "DB20240220YHCS1009",
  "sellerTaxNo": "DB20240220YHCS1009",
  "redConfirmUuid": "uuid-string",
  "redConfirmNo": "",
  "taxUserName": ""
}
```

Response includes:
- `electricInvoiceDetails` — line items
- `redPdfUrl` — downloadable PDF
- `alreadyRedInvoiceFlag` — `"Y"` / `"N"` whether red invoice was already issued
- `confirmState` — current state

---

## 6. Error Codes Reference

| Error Code | Meaning | Action |
|-----------|---------|--------|
| `100001` / `100002` | Token invalid/expired | Re-authenticate |
| `100007` | Wrong signature | Check sign computation |
| `20019` | Invalid invoiceTypeCode | Use valid code |
| `20020` | No terminal found | Use `01`/`02` (no hardware needed) |
| `20023` | No e-invoice terminal | Same as above |
| `70169` | Required param empty | Check mandatory fields |
| `70035` | Red form operation error | Check state allows the operation |

---

## 7. Quick Visual Reference

```
┌─────────────────────────────────────────────────────────┐
│ URL Query String                                         │
│  method, version, appKey, format, timestamp, type,       │
│  requestId, token, sign                                  │
│  [v7.0 only]: signType, encryptType, encryptScope        │
├─────────────────────────────────────────────────────────┤
│ JSON Body (compact, no spaces)                           │
│  Pattern A (v6.0+data): { "taxNo":"...", "data":{...} }  │
│  Pattern B (v7.0 flat): { "taxNo":"...", "k":"v", ... }  │
│  Pattern C (v6.0 flat): { "taxNo":"...", "k":"v", ... }  │
├─────────────────────────────────────────────────────────┤
│ Sign = MD5(                                              │
│   appSecret                                              │
│   + sorted(key+value for each URL param, skip empties)   │
│   + raw_compact_json_body                                │
│   + appSecret                                            │
│ ).upper()                                                │
└─────────────────────────────────────────────────────────┘
```


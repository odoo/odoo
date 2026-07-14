"""
Baiwang API Test Script
=======================
Quick test to verify authentication and basic API calls against
the Baiwang sandbox. Fill in your credentials below and run.

Usage:
    python baiwang_test.py
"""

import hashlib
import json
import time
import uuid

import requests

# ═══════════════════════════════════════════════════════════════
# FILL IN YOUR SANDBOX CREDENTIALS HERE
# ═══════════════════════════════════════════════════════════════
APP_KEY = "1004139"           # Your appKey
APP_SECRET = "15719e2a-89b7-4032-acc0-ff62151d1bbb"        # Your appSecret
USERNAME = "admin_rsmc17paj2ic8"           # Login username
PASSWORD = "Aa1234567Aa"           # Login password (raw, will be hashed)
SECRET = "15258c22aa1349819e8cf20c0da04956"             # Salt/secret for password hashing
TAX_NO = "DB20240220YHCS1009"             # e.g. "DB20240220YHCS1009"
ORG_AUTH_CODE = ""      # orgAuthCode (required for 3rd-party apps, optional for internal)

ENDPOINT = "https://sandbox-openapi.baiwang.com/router/rest"
# ═══════════════════════════════════════════════════════════════


def md5(data: str) -> str:
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def hash_password(password: str, secret: str) -> str:
    """Hash password as: SHA256(password + salt)"""
    return sha256(password + secret)


def compute_sign(url_params: dict, app_secret: str, body_str: str = '') -> str:
    """
    Baiwang API request signing.

    Formula: MD5(appSecret + sorted(key+value for non-empty url_params) + body_json_str + appSecret).upper()

    - url_params: the URL query parameters (excluding 'sign' itself)
    - body_str: the raw JSON body string (compact, no spaces)
    """
    sorted_keys = sorted(url_params.keys())
    string_to_sign = app_secret

    for key in sorted_keys:
        value = url_params.get(key)
        if not key or value is None or (isinstance(value, str) and not value.strip()):
            continue
        string_to_sign += str(key) + str(value)

    string_to_sign += body_str
    string_to_sign += app_secret
    return md5(string_to_sign).upper()


def call_api(method: str, data_content: dict | None = None, token: str | None = None,
             top_level_body: dict | None = None, quiet: bool = False,
             version: str = '6.0', flat_body: dict | None = None):
    """
    Make a business API call to Baiwang.

    Per docs:
      URL query params: method, version, appKey, format, timestamp, token, type, requestId, sign
                        (+ signType, encryptType, encryptScope for v7.0 APIs)
      JSON body varies by endpoint:
        - v6.0 style: { "taxNo": "...", "data": {...} }
        - v7.0 style (flat): { "taxNo": "...", all fields at top level... }

    Sign = MD5(appSecret + sorted_url_params + raw_body_json + appSecret).upper()
    """
    request_id = str(uuid.uuid4())

    # URL query parameters (routing + auth)
    url_params = {
        'method': method,
        'version': version,
        'appKey': APP_KEY,
        'format': 'json',
        'timestamp': str(int(time.time() * 1000)),
        'type': 'sync',
        'requestId': request_id,
    }
    if token:
        url_params['token'] = token

    # v7.0 APIs require these additional URL params
    if version == '7.0':
        url_params['signType'] = 'MD5'
        url_params['encryptType'] = 'NONE'
        url_params['encryptScope'] = '00'

    # Build JSON body
    if flat_body is not None:
        # v7.0 flat body style (no "data" wrapper)
        body = flat_body
    else:
        # v6.0 style with "data" wrapper
        body = {}
        if top_level_body:
            body.update(top_level_body)
        if data_content:
            body['data'] = data_content

    # Compact JSON body string (must match exactly what we send)
    body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))

    # Compute signature
    url_params['sign'] = compute_sign(url_params, APP_SECRET, body_str)

    if not quiet:
        print(f"Calling {method} (requestId={request_id})")

    response = requests.post(
        ENDPOINT,
        params=url_params,
        data=body_str.encode('utf-8'),
        headers={'Content-Type': 'application/json; charset=utf-8'},
        timeout=15,
    )

    if not quiet:
        print(f"HTTP {response.status_code}")
    try:
        result = response.json()
        if not quiet:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return result
    except ValueError:
        if not quiet:
            print(f"Failed to parse JSON response: {response.text[:500]}")
        return None


def test_auth():
    """
    Get access token following official docs.

    URL query params: method, grant_type, client_id, version(7.0), timestamp, encryptType, encryptScope
    JSON body: password, username, client_secret, orgAuthCode
    Password: SHA256(plaintext_password + salt)
    """

    hashed_pw = hash_password(PASSWORD, SECRET)

    # URL query parameters
    url_params = {
        'method': 'baiwang.oauth.token',
        'grant_type': 'password',
        'client_id': APP_KEY,
        'version': '7.0',
        'timestamp': str(int(time.time() * 1000)),
        'encryptType': 'NONE',
        'encryptScope': '00',
    }

    # JSON body
    body = {
        'password': hashed_pw,
        'username': USERNAME,
        'client_secret': APP_SECRET,
    }
    if ORG_AUTH_CODE:
        body['orgAuthCode'] = ORG_AUTH_CODE

    response = requests.post(
        ENDPOINT,
        params=url_params,
        json=body,
        timeout=15,
    )

    try:
        result = response.json()
    except ValueError:
        return None

    if result and result.get('success'):
        return result.get('response', {}).get('access_token')
    return None


def test_terminal_query(token: str):
    """
    Query terminal info - try with empty filters to get ALL terminals.
    """

    # Query with empty data to get all terminals
    result = call_api(
        method='baiwang.output.terminal.query',
        data_content={
            'invoiceTerminalCode': '',
            'invoiceTerminalName': '',
            'invoiceTypeCode': '',
            'machineNo': '',
            'taxDiskNo': '',
            'deviceType': '',
            'defaultInvoiceTypeCodes': '',
        },
        token=token,
        top_level_body={'taxNo': TAX_NO},
    )

    if result and result.get('success'):
        terminals = result.get('response', [])
        if terminals:
            for t in terminals:
                pass
        return terminals
    return None


def test_invoice_issue_all_types(token: str, terminal_code: str | None = None):
    """
    Try issuing invoices with various invoiceTypeCode values.
    Known codes: 004, 005, 006, 007, 025, 026, 028
    Also try: 001-010, 020-030, and some others.
    """

    # Known + exploratory codes
    codes_to_try = [
        '004',  # VAT Special Invoice
        '005',  # mentioned in terminal response
        '006',  # mentioned in terminal response
        '007',  # VAT General Invoice
        '025',  # VAT Volume Invoice
        '026',  # VAT Electronic Invoice
        '028',  # VAT Special Electronic Invoice
        # Exploratory - all electric / digital invoice codes
        '001', '002', '003',
        '008', '009', '010',
        '020', '021', '022', '023', '024',
        '027', '029', '030',
        '031', '032', '033',
        # Fully-digital (全电) types often use 2-digit-like codes
        '01', '02', '03', '04', '05',
    ]

    results = {}
    for code in codes_to_try:
        serial = f'TYPE_TEST_{code}_{int(time.time())}'
        invoice_data = {
            'invoiceType': '0',
            'invoiceTypeCode': code,
            'priceTaxMark': '0',
            'invoiceListMark': '0',
            'taxationMethod': '0',
            'serialNo': serial,
            'buyerName': 'Test Buyer Company',
            'buyerTaxNo': '91110108MA01KPGP0L',
            'invoiceTotalPrice': 2.0,
            'invoiceTotalTax': 0.2,
            'invoiceTotalPriceTax': 2.2,
            'invoiceDetailsList': [
                {
                    'goodsLineNo': 1,
                    'invoiceLineNature': '0',
                    'goodsCode': '1010101070000000000',
                    'goodsName': '燕麦',
                    'goodsTaxRate': 0.1,
                    'goodsTotalPrice': 2.0,
                    'goodsTotalTax': 0.2,
                    'preferentialMarkFlag': '0',
                },
            ],
        }

        top_body = {'taxNo': TAX_NO}
        if terminal_code:
            top_body['invoiceTerminalCode'] = terminal_code

        result = call_api(
            method='baiwang.output.invoice.issue',
            data_content=invoice_data,
            token=token,
            top_level_body=top_body,
            quiet=True,
        )

        if result:
            success = result.get('success', False)
            if success:
                status = '✅ SUCCESS'
                detail = json.dumps(result.get('response'), ensure_ascii=False)[:100]
            else:
                err = result.get('errorResponse', {})
                status = '❌ FAILED'
                detail = f"[{err.get('subCode', err.get('code'))}] {err.get('subMessage', err.get('message', ''))}"
        else:
            status = '❌ NO RESPONSE'
            detail = ''

        results[code] = (status, detail)
        time.sleep(0.3)  # Be gentle with the sandbox

    # Summary
    for code, (status, detail) in results.items():
        pass

    return results


def test_redinvoice_add(token: str, blue_invoice_no: str | None = None):
    """
    Test: Red letter confirmation (baiwang.output.redinvoice.add)

    This is a v7.0 API with flat body (no "data" wrapper).
    In production, this would reference a real blue invoice number.
    For sandbox testing, we use the invoice number from our successful issue.
    """

    # Use the blue invoice number if provided, otherwise use a test value
    original_invoice_no = blue_invoice_no or '00000000000000000000'

    # Flat body - all fields at top level (v7.0 style, no "data" wrapper)
    body = {
        'taxNo': TAX_NO,
        'redConfirmSerialNo': f'RED_{int(time.time())}',
        'entryIdentity': '01',              # 01=seller side
        'sellerTaxNo': TAX_NO,
        'sellerTaxName': 'Test Seller Company',
        'buyerTaxName': 'Test Buyer Company',
        'buyerTaxNo': '91110108MA01KPGP0L',
        'originInvoiceIsPaper': 'N',        # N=electronic
        'originalInvoiceNo': original_invoice_no,
        'originInvoiceDate': '2026-05-21 10:00:00',
        'originInvoiceTotalPrice': 2.0,
        'originInvoiceTotalTax': 0.2,
        'originInvoiceType': '02',          # 02=普通发票 (matches our blue invoice type)
        'invoiceTotalPrice': -2.0,          # Negative for red
        'invoiceTotalTax': -0.2,            # Negative for red
        'redInvoiceLabel': '01',            # 01=开票有误 (billing error)
        'invoiceSource': '2',               # 2=电子发票服务平台 (digital platform)
        'priceTaxMark': '0',                # 0=prices exclude tax
        'autoIssueSwitch': 'N',             # N=don't auto-issue red invoice
        'deliverFlag': '0',
        'redInvoiceIsPaper': 'N',
        'redConfirmDetailReqEntityList': [
            {
                'originalInvoiceDetailNo': 1,
                'goodsLineNo': 1,
                'goodsCode': '1010101070000000000',
                'goodsName': '*谷物*燕麦',
                'goodsSimpleName': '谷物',
                'projectName': '燕麦',
                'goodsTaxRate': 0.1,
                'goodsTotalPrice': -2.0,
                'goodsTotalTax': -0.2,
                'goodsQuantity': '-1',
                'goodsPrice': '2.0',
                'goodsUnit': '份',
            },
        ],
        # Optional fields (empty strings)
        'originalPaperInvoiceCode': '',
        'originalPaperInvoiceNo': '',
        'orgCode': '',
        'accessPlatformNo': '',
        'taxUserName': '',
        'drawer': '',
        'drawerCredentialsType': '',
        'drawerCredentialsNo': '',
        'buyerEmail': '',
        'buyerPhone': '',
        'originInvoiceSetCode': '',
        'ext': {},
    }

    result = call_api(
        method='baiwang.output.redinvoice.add',
        token=token,
        flat_body=body,
        version='7.0',
    )

    if result and result.get('success'):
        resp = result.get('response', [])
        if resp:
            for r in resp:
                pass
        return resp
    result.get('errorResponse', {}) if result else {}
    return None


def test_redinvoice_operate(token: str, red_confirm_uuid: str, red_confirm_no: str):
    """
    Test: Red letter operate (baiwang.output.redinvoice.operate)
    Actions: 01=confirm, 02=deny, 03=revoke

    v7.0, flat body.
    """

    # Try to REVOKE (03) the red confirmation we created
    body = {
        'taxNo': TAX_NO,
        'sellerTaxNo': TAX_NO,
        'redConfirmUuid': red_confirm_uuid,
        'redConfirmNo': red_confirm_no,
        'confirmType': '03',        # 03=revoke/撤销
        'taxUserName': '',
    }

    result = call_api(
        method='baiwang.output.redinvoice.operate',
        token=token,
        flat_body=body,
        version='7.0',
    )

    if result and result.get('success'):
        resp = result.get('response', [])
        if resp:
            for r in resp:
                pass
        return resp
    result.get('errorResponse', {}) if result else {}
    return None


def test_redinvoice_formlist(token: str):
    """
    Test: Red letter form list query (baiwang.output.redinvoice.formlist)

    v7.0, flat body. Query all red confirmations for our tax number.
    """

    body = {
        'taxNo': TAX_NO,
        'sellerTaxNo': TAX_NO,
        'buySelSelector': '0',          # 0=seller role
        'entryIdentity': '01',          # 01=seller
        'pageNo': 1,
        'pageSize': 10,
        'queryAll': True,
        # Optional filters (empty = no filter)
        'buyerTaxNo': '',
        'confirmState': '',
        'originalInvoiceNo': '',
        'redConfirmNo': '',
        'redConfirmSerialNo': '',
        'invoiceStartDate': '2026-05-21',
        'invoiceEndDate': '2026-05-22',
        'confirmStartDate': '',
        'confirmEndDate': '',
        'originalPaperInvoiceCode': '',
        'originalPaperInvoiceNo': '',
        'organizationCode': '',
        'dataSource': '',
        'taxUserName': '',
        'ext': {},
    }

    result = call_api(
        method='baiwang.output.redinvoice.formlist',
        token=token,
        flat_body=body,
        version='7.0',
    )

    if result and result.get('success'):
        resp = result.get('response', [])
        if resp:
            for r in resp:
                pass
        return resp
    result.get('errorResponse', {}) if result else {}
    return None


def test_redinvoice_redforminfo(token: str, red_confirm_uuid: str):
    """
    Test: Red letter detail query (baiwang.output.redinvoice.redforminfo)

    v6.0, flat body (no "data" wrapper, no signType/encryptType in URL).
    """

    body = {
        'taxNo': TAX_NO,
        'sellerTaxNo': TAX_NO,
        'redConfirmUuid': red_confirm_uuid,
        'redConfirmNo': '',
        'taxUserName': '',
    }

    result = call_api(
        method='baiwang.output.redinvoice.redforminfo',
        token=token,
        flat_body=body,
        version='6.0',
    )

    if result and result.get('success'):
        resp = result.get('response', [])
        if resp:
            for r in resp:
                details = r.get('electricInvoiceDetails', [])
                if details:
                    for d in details:
                        pass
        return resp
    result.get('errorResponse', {}) if result else {}
    return None


def main():
    if not all([APP_KEY, APP_SECRET, USERNAME, PASSWORD, SECRET, TAX_NO]):
        return

    # Test 1: Auth
    token = test_auth()
    if not token:
        return

    # Test 2: Terminal query
    test_terminal_query(token)

    # Test 3: Issue a blue invoice (type 02)
    blue_invoice_no = None
    blue_result = call_api(
        method='baiwang.output.invoice.issue',
        data_content={
            'invoiceType': '0',
            'invoiceTypeCode': '02',
            'priceTaxMark': '0',
            'invoiceListMark': '0',
            'taxationMethod': '0',
            'serialNo': f'BLUE_{int(time.time())}',
            'buyerName': 'Test Buyer Company',
            'buyerTaxNo': '91110108MA01KPGP0L',
            'invoiceTotalPrice': 2.0,
            'invoiceTotalTax': 0.2,
            'invoiceTotalPriceTax': 2.2,
            'invoiceDetailsList': [
                {
                    'goodsLineNo': 1,
                    'invoiceLineNature': '0',
                    'goodsCode': '1010101070000000000',
                    'goodsName': '燕麦',
                    'goodsTaxRate': 0.1,
                    'goodsTotalPrice': 2.0,
                    'goodsTotalTax': 0.2,
                    'preferentialMarkFlag': '0',
                },
            ],
        },
        token=token,
        top_level_body={'taxNo': TAX_NO},
    )
    if blue_result and blue_result.get('success'):
        success_list = blue_result.get('response', {}).get('success', [])
        if success_list:
            blue_invoice_no = success_list[0].get('invoiceNo')
            raw_date = success_list[0].get('invoiceDate', '')
            # Convert from "20260521152632" to "2026-05-21 15:26:32"
            if len(raw_date) >= 14:
                f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]} {raw_date[8:10]}:{raw_date[10:12]}:{raw_date[12:14]}"
    if not blue_invoice_no:
        print('Blue invoice issue did not return an invoice number; red-invoice tests may use fallback values.')

    # Test 4: Red letter confirmation (references blue invoice)
    red_info = test_redinvoice_add(token, blue_invoice_no)
    red_confirm_uuid = None
    if red_info:
        red_confirm_uuid = red_info[0].get('redConfirmUuid')
        red_info[0].get('redConfirmNo')

    # Test 5: Red form detail query (get full info about the red confirmation)
    if red_confirm_uuid:
        test_redinvoice_redforminfo(token, red_confirm_uuid)

    # Test 6: Red form list query (search all red confirmations)
    test_redinvoice_formlist(token)

    # Test 7: Red invoice operate (try to revoke)
    # Issue a NEW red confirmation specifically for revoke testing
    blue2 = call_api(
        method='baiwang.output.invoice.issue',
        data_content={
            'invoiceType': '0',
            'invoiceTypeCode': '02',
            'priceTaxMark': '0',
            'invoiceListMark': '0',
            'taxationMethod': '0',
            'serialNo': f'BLUE2_{int(time.time())}',
            'buyerName': 'Test Buyer Company',
            'buyerTaxNo': '91110108MA01KPGP0L',
            'invoiceTotalPrice': 3.0,
            'invoiceTotalTax': 0.3,
            'invoiceTotalPriceTax': 3.3,
            'invoiceDetailsList': [
                {
                    'goodsLineNo': 1,
                    'invoiceLineNature': '0',
                    'goodsCode': '1010101070000000000',
                    'goodsName': '燕麦',
                    'goodsTaxRate': 0.1,
                    'goodsTotalPrice': 3.0,
                    'goodsTotalTax': 0.3,
                    'preferentialMarkFlag': '0',
                },
            ],
        },
        token=token,
        top_level_body={'taxNo': TAX_NO},
        quiet=True,
    )
    blue2_no = None
    blue2_date = None
    if blue2 and blue2.get('success'):
        sl = blue2.get('response', {}).get('success', [])
        if sl:
            blue2_no = sl[0].get('invoiceNo')
            rd = sl[0].get('invoiceDate', '')
            if len(rd) >= 14:
                blue2_date = f"{rd[:4]}-{rd[4:6]}-{rd[6:8]} {rd[8:10]}:{rd[10:12]}:{rd[12:14]}"

    if blue2_no:
        # Create red confirmation with autoIssueSwitch=N so we can revoke it
        red2_body = {
            'taxNo': TAX_NO,
            'redConfirmSerialNo': f'RED2_{int(time.time())}',
            'entryIdentity': '01',
            'sellerTaxNo': TAX_NO,
            'sellerTaxName': 'Test Seller Company',
            'buyerTaxName': 'Test Buyer Company',
            'buyerTaxNo': '91110108MA01KPGP0L',
            'originInvoiceIsPaper': 'N',
            'originalInvoiceNo': blue2_no,
            'originInvoiceDate': blue2_date or '2026-05-21 10:00:00',
            'originInvoiceTotalPrice': 3.0,
            'originInvoiceTotalTax': 0.3,
            'originInvoiceType': '02',
            'invoiceTotalPrice': -3.0,
            'invoiceTotalTax': -0.3,
            'redInvoiceLabel': '01',
            'invoiceSource': '2',
            'priceTaxMark': '0',
            'autoIssueSwitch': 'N',
            'deliverFlag': '0',
            'redInvoiceIsPaper': 'N',
            'redConfirmDetailReqEntityList': [{
                'originalInvoiceDetailNo': 1,
                'goodsLineNo': 1,
                'goodsCode': '1010101070000000000',
                'goodsName': '*谷物*燕麦',
                'goodsSimpleName': '谷物',
                'projectName': '燕麦',
                'goodsTaxRate': 0.1,
                'goodsTotalPrice': -3.0,
                'goodsTotalTax': -0.3,
                'goodsQuantity': '-1',
                'goodsPrice': '3.0',
                'goodsUnit': '份',
            }],
            'originalPaperInvoiceCode': '',
            'originalPaperInvoiceNo': '',
            'orgCode': '',
            'accessPlatformNo': '',
            'taxUserName': '',
            'drawer': '',
            'drawerCredentialsType': '',
            'drawerCredentialsNo': '',
            'buyerEmail': '',
            'buyerPhone': '',
            'originInvoiceSetCode': '',
            'ext': {},
        }
        red2_result = call_api(
            method='baiwang.output.redinvoice.add',
            token=token,
            flat_body=red2_body,
            version='7.0',
            quiet=True,
        )
        if red2_result and red2_result.get('success'):
            red2_resp = red2_result.get('response', [])
            if red2_resp:
                r2_uuid = red2_resp[0].get('redConfirmUuid')
                r2_no = red2_resp[0].get('redConfirmNo')
                red2_resp[0].get('confirmState')

                # Now try to REVOKE it
                test_redinvoice_operate(token, r2_uuid, r2_no)
        else:
            red2_result.get('errorResponse', {}) if red2_result else {}


if __name__ == '__main__':
    main()

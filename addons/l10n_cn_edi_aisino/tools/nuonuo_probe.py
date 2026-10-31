#!/usr/bin/env python3
# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Read-only probe of the Nuonuo 诺税通 saas API, the provider Aisino is compared against.

Lives next to probe.py so both sides of the comparison can be re-run the same way.
Standalone: stdlib only, no Odoo.

    # credentials: NUONUO_APP_KEY/APP_SECRET/TOKEN/TAX_NO, exported or in
    # ~/.config/l10n_cn_edi/probe.env (chmod 600, never in the repo) — see local_env.py
    python3 nuonuo_probe.py sign       # offline: print the canonical string and signature
    python3 nuonuo_probe.py invoice    # 1 request: a query for an order that does not exist
    python3 nuonuo_probe.py redform    # 1 request: red-confirmation forms of the last 90 days
    python3 nuonuo_probe.py auth       # 2 requests: stored 全电 login + 开票认证 status (query mode only)
    python3 nuonuo_probe.py sandbox    # 1 request: does the sandbox accept these credentials?
    python3 nuonuo_probe.py all

The 联调 account is a test account on the PRODUCTION gateway, and the vendor's note
says 请勿压测，真的会封IP. So: only methods in READ_ONLY can be called, requests are
serialized and spaced by SPACING seconds, and one run never sends more than MAX_REQUESTS.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import date, timedelta

import local_env  # noqa: E402

local_env.load()

ENDPOINT = 'https://sdk.nuonuo.com/open/v1/services'
SANDBOX = 'https://sandbox.nuonuocs.cn/open/v1/services'
READ_ONLY = {
    'nuonuo.OpeMplatform.queryInvoiceResult',
    'nuonuo.OpeMplatform.queryInvoiceRedConfirm',
    'nuonuo.OpeMplatform.getCertificationStatus',
}
# queryType 0 refreshes against the tax bureau (20/day, 30 s apart); 1 and 2 read Nuonuo's stored state.
QUERY_ONLY = {'nuonuo.OpeMplatform.getCertificationStatus': ('queryType', {'1', '2'})}
EXTENSION_NUMBER = '923'  # 分机号 that can issue 数电 invoices on the 联调 account
SPACING = 6
MAX_REQUESTS = 5


def sign(app_secret, app_key, senid, nonce, timestamp, content):
    """X-Nuonuo-Sign: base64(HMAC-SHA1) over the fixed-path canonical string.

    The path /open/v1/services is spelled a=services&l=v1&p=open, and f is the exact
    request body. Validated against the production gateway on 2026-09-22.
    """
    message = f'a=services&l=v1&p=open&k={app_key}&i={senid}&n={nonce}&t={timestamp}&f={content}'
    digest = hmac.new(app_secret.encode(), message.encode(), hashlib.sha1).digest()
    return message, base64.b64encode(digest).decode()


class Probe:
    def __init__(self):
        self.app_key = os.environ.get('NUONUO_APP_KEY', '')
        self.app_secret = os.environ.get('NUONUO_APP_SECRET', '')
        self.token = os.environ.get('NUONUO_TOKEN', '')
        self.tax_no = os.environ.get('NUONUO_TAX_NO', '')
        self.sent = 0

    def _require_creds(self):
        missing = [name for name, value in (
            ('NUONUO_APP_KEY', self.app_key),
            ('NUONUO_APP_SECRET', self.app_secret),
            ('NUONUO_TOKEN', self.token),
            ('NUONUO_TAX_NO', self.tax_no),
        ) if not value]
        if missing:
            sys.exit(f"missing env: {', '.join(missing)}")

    def call(self, method, payload, endpoint=ENDPOINT):
        if method not in READ_ONLY:
            sys.exit(f'refusing {method}: not a known read-only method')
        if method in QUERY_ONLY:
            field, allowed = QUERY_ONLY[method]
            if payload.get(field) not in allowed:
                sys.exit(f'refusing {method}: {field}={payload.get(field)!r} is not a query')
        if self.sent >= MAX_REQUESTS:
            sys.exit(f'refusing {method}: request cap of {MAX_REQUESTS} reached')
        self._require_creds()
        if self.sent:
            time.sleep(SPACING)
        self.sent += 1

        content = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        senid = uuid.uuid4().hex
        nonce = str(random.randint(10_000_000, 99_999_999))
        timestamp = str(int(time.time()))
        _message, signature = sign(self.app_secret, self.app_key, senid, nonce, timestamp, content)
        query = f'senid={senid}&nonce={nonce}&timestamp={timestamp}&appkey={self.app_key}'
        request = urllib.request.Request(
            f'{endpoint}?{query}',
            data=content.encode('utf-8'),
            headers={
                'Content-Type': 'application/json; charset=UTF-8',
                'X-Nuonuo-Sign': signature,
                'accessToken': self.token,
                'userTax': self.tax_no,
                'method': method,
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as error:
            print(f'  {method} -> HTTP {error.code}: {error.read().decode("utf-8", "replace")[:200]}')
            return {}
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            print(f'  {method} -> not JSON: {raw[:200]}')
            return {}
        print(f'  {method} -> {body.get("code")} {body.get("describe")}')
        return body

    def phase_sign(self):
        """Offline: show exactly what gets signed, for comparing against another client."""
        print('== sign (offline) ==')
        message, signature = sign('SECRET', 'APPKEY', 'SENID', '12345678', '1700000000', '{"a":1}')
        print(f'  {message}\n  -> {signature}')

    def phase_invoice(self):
        """A business-level 'not found' (E9500) proves the signature and headers are right."""
        print('== invoice ==')
        self.call('nuonuo.OpeMplatform.queryInvoiceResult', {
            'orderNos': ['PROBE-NONEXISTENT-ORDER-0000000000'],
            'isOfferInvoiceDetail': '0',
        })

    def phase_redform(self):
        """The dates are required once no bill id is given, despite the doc marking them optional."""
        print('== redform ==')
        today = date.today()
        body = self.call('nuonuo.OpeMplatform.queryInvoiceRedConfirm', {
            'identity': '0',
            'billTimeStart': (today - timedelta(days=89)).isoformat(),
            'billTimeEnd': today.isoformat(),
            'pageNo': '1',
            'pageSize': '1',
        })
        result = body.get('result') or {}
        print(f'  total forms visible to this account: {result.get("total")}')

    def phase_auth(self):
        """Can we tell the tax-bureau session has lapsed before an invoice fails on it?"""
        print('== auth ==')
        for query_type, label in (('2', '全电登录状态'), ('1', '开票认证状态')):
            body = self.call('nuonuo.OpeMplatform.getCertificationStatus', {
                'extensionNumber': EXTENSION_NUMBER,
                'queryType': query_type,
            })
            print(f'  {label}: {json.dumps(body.get("result"), ensure_ascii=False)}')

    def phase_sandbox(self):
        """The sandbox would allow write testing; a signature or app error means it needs its own app."""
        print('== sandbox ==')
        self.call('nuonuo.OpeMplatform.queryInvoiceResult', {
            'orderNos': ['PROBE-NONEXISTENT-ORDER-0000000000'],
            'isOfferInvoiceDetail': '0',
        }, endpoint=SANDBOX)

    def phase_all(self):
        self.phase_sign()
        self.phase_invoice()
        self.phase_redform()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('phase', choices=['sign', 'invoice', 'redform', 'auth', 'sandbox', 'all'])
    getattr(Probe(), f'phase_{parser.parse_args().phase}')()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Probe the Aisino Yunshui (爱信诺云税) sandbox once credentials land.

Answers the questions their 20260909 reply sheet left open, without asking them
again. Standalone: no Odoo, stdlib + the sibling crypto module only.

    export AISINO_IDENTITY_CODE=...   # 授权码
    export AISINO_PLATFORM_CODE=...   # 组织编码
    export AISINO_TAX_NO=...          # 税号
    python3 probe.py envelope         # offline, run this first
    python3 probe.py auth             # is our envelope right? (read-only)
    python3 probe.py keyvariant       # only if auth fails: which derivation works?
    python3 probe.py redform          # RPA-or-API characterisation (read-only)
    python3 probe.py ratelimit        # opt-in ramp (read-only)
    python3 probe.py margin           # 差额发票, WRITES - needs --allow-writes
    python3 probe.py all              # every read-only phase

Endpoints and interface codes come from the v1.8.2 spec; section numbers moved
in v1.8.4, so everything here is keyed on 接口编码, never on "2.1.x".
"""
import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crypto import sm4_envelope as env  # noqa: E402

HOSTS = {
    'test': 'https://llys.51fapiao.cn/openapi',   # 测试环境
    'prod': 'https://ll.51fapiao.cn/openapi',     # 生产环境
}

CODES = {
    'tax_codes': 'smartCoding.batchTaxCode',      # read-only, no login needed
    'enterprise_card': 'ele.query.gfxx2',         # read-only
    'credit_line': 'ele.creditLine',              # read-only, needs login
    'red_form_query': 'ele.hzqrd.query',          # read-only
    'invoice_issue': 'ele.encrypt.invoiceIssue',  # WRITES
    'query_result': 'ele.encrypt.queryResult',
    'process_order': 'ele.encrypt.processOrder',  # WRITES
    'login': 'ele.eleLogin',
}


class Probe:
    def __init__(self, args):
        self.base = HOSTS[args.host]
        self.identity = os.environ.get('AISINO_IDENTITY_CODE', '')
        self.platform = os.environ.get('AISINO_PLATFORM_CODE', '')
        self.tax_no = os.environ.get('AISINO_TAX_NO', '')
        self.timeout = args.timeout
        self.allow_writes = args.allow_writes
        self.findings = {}
        if args.host == 'prod' and not args.i_mean_production:
            sys.exit('refusing prod without --i-mean-production')

    def _require_creds(self):
        missing = [n for n, v in (
            ('AISINO_IDENTITY_CODE', self.identity),
            ('AISINO_PLATFORM_CODE', self.platform),
            ('AISINO_TAX_NO', self.tax_no),
        ) if not v]
        if missing:
            sys.exit(f"missing env: {', '.join(missing)}")

    def call(self, code, payload, key_override=None, timestamp=None):
        """POST one enveloped request. Returns (elapsed_s, http_status, parsed_or_raw)."""
        ts = timestamp or env.now_timestamp()
        if key_override is None:
            body = env.build_request(code, payload, self.identity, self.platform,
                                     self.tax_no, timestamp=ts)
        else:
            # hand-rolled so a non-standard key derivation can be tried
            access_token = env.make_access_token(self.platform, self.tax_no, ts)
            json_str = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            datagram = env._build_datagram(json_str, key_override, '0')
            body = {
                'interfaceCode': code, 'zipCode': '0', 'encryptCode': env.ENCRYPT_CODE,
                'access_token': access_token, 'datagram': datagram,
                'signtype': env.SIGNTYPE,
                'signature': env.sign(code, '0', env.ENCRYPT_CODE, access_token,
                                      datagram, env.SIGNTYPE, key_override),
            }
        req = urllib.request.Request(
            f'{self.base}/{code}',
            data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode('utf-8', 'replace')
                status = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', 'replace')
            status = exc.code
        except Exception as exc:  # noqa: BLE001 - a timeout IS the finding here
            return time.monotonic() - started, None, f'{type(exc).__name__}: {exc}'
        elapsed = time.monotonic() - started
        try:
            return elapsed, status, json.loads(raw)
        except json.JSONDecodeError:
            return elapsed, status, raw  # HTML error page is itself a finding

    # --- phase 0: offline -------------------------------------------------

    def phase_envelope(self):
        """Prove the envelope round-trips before blaming the network for anything."""
        print('== envelope (offline) ==')
        ok = True
        for zip_code in ('0', '1', '2'):
            payload = {'probe': 'ok', '中文': '测试', 'n': 1234.56}
            req = env.build_request('x', payload, 'IDENT', 'PLAT', 'TAX',
                                    timestamp='20231014180655', zip_code=zip_code)
            back = env.verify_and_decrypt(
                dict(req, code='1000'), 'IDENT', 'PLAT')
            good = back == payload
            ok &= good
            print(f'  zipCode {zip_code}: {"ok" if good else "MISMATCH"}')
        if self.identity and self.platform:
            ts = env.now_timestamp()
            print(f'\n  key candidates for ts={ts}:')
            for name, key in self._key_variants(ts).items():
                print(f'    {name:16} {key!r}')
            print('  (we ship "middle16"; the spec prose says "16 位 MD5",')
            print('   the Java demo says substring(8, 24) -- that is the ambiguity)')
        self.findings['envelope_roundtrip'] = ok
        return ok

    def _key_variants(self, ts):
        import hashlib
        md5hex = hashlib.md5(
            (self.identity + self.platform + ts).encode('utf-8')).hexdigest()
        return {
            'middle16': md5hex[8:24].encode(),   # what we implement
            'first16': md5hex[:16].encode(),
            'last16': md5hex[16:].encode(),
            'hexdecoded8': bytes.fromhex(md5hex[8:24]),  # 8 bytes, likely invalid
        }

    # --- phase 1: is the envelope right? ----------------------------------

    def phase_auth(self):
        """Cheapest read-only call. A non-signature error means the envelope is fine."""
        self._require_creds()
        print('== auth (envelope against the real server) ==')
        code = CODES['tax_codes']
        elapsed, status, body = self.call(code, {'pageNo': 1, 'pageSize': 1})
        print(f'  {code} -> HTTP {status} in {elapsed:.2f}s')
        print(f'  {json.dumps(body, ensure_ascii=False)[:400] if isinstance(body, dict) else str(body)[:400]}')
        outer = body.get('code') if isinstance(body, dict) else None
        sig_error = outer in ('9995', '9996') or 'sign' in str(body).lower()
        self.findings['auth'] = {'status': status, 'outer_code': outer,
                                 'signature_rejected': bool(sig_error)}
        if sig_error:
            print('\n  SIGNATURE REJECTED -> run:  probe.py keyvariant')
        elif outer == '1000':
            print('\n  envelope accepted, key derivation confirmed')
        else:
            print(f'\n  envelope accepted at transport level; business code {outer}')
        return not sig_error

    def phase_keyvariant(self):
        """Only worth running if auth failed: try every plausible key derivation."""
        self._require_creds()
        print('== keyvariant (which SM4 key does the server expect?) ==')
        code = CODES['tax_codes']
        ts = env.now_timestamp()
        for name, key in self._key_variants(ts).items():
            if len(key) != 16:
                print(f'  {name:16} skipped ({len(key)} bytes, SM4 needs 16)')
                continue
            try:
                _, status, body = self.call(code, {'pageNo': 1, 'pageSize': 1},
                                            key_override=key, timestamp=ts)
            except Exception as exc:  # noqa: BLE001
                print(f'  {name:16} raised {exc}')
                continue
            outer = body.get('code') if isinstance(body, dict) else '?'
            msg = body.get('msg', '') if isinstance(body, dict) else str(body)[:60]
            verdict = 'ACCEPTED' if outer == '1000' else f'rejected {outer} {msg}'
            print(f'  {name:16} HTTP {status} -> {verdict}')
            self.findings.setdefault('key_variants', {})[name] = verdict

    # --- phase 2: RPA or API? ---------------------------------------------

    def phase_redform(self, samples=8):
        """Latency spread and error shape say more than their naming does.

        A real API answers fast and consistently, and rejects junk with a code.
        Something driving the bureau's H5 portal is slow, jittery, and tends to
        surface timeouts or HTML instead.
        """
        self._require_creds()
        print('== redform (read-only characterisation) ==')
        code = CODES['red_form_query']
        times = []
        for i in range(samples):
            elapsed, status, body = self.call(code, {'pageNo': 1, 'pageSize': 10})
            times.append(elapsed)
            outer = body.get('code') if isinstance(body, dict) else 'non-json'
            print(f'  #{i + 1} {elapsed:6.2f}s HTTP {status} code={outer}')
        if times:
            spread = max(times) / max(min(times), 0.001)
            print(f'\n  min {min(times):.2f}s  median {statistics.median(times):.2f}s  '
                  f'max {max(times):.2f}s  spread x{spread:.1f}')
            print('  >2s median or >3x spread reads like automation, not an API')
            self.findings['redform_latency'] = {
                'min': min(times), 'median': statistics.median(times),
                'max': max(times), 'spread': spread}

        print('\n  -- malformed input, what shape is the error? --')
        _, status, body = self.call(code, {'pageNo': 'not-a-number', 'bogus': '???'})
        kind = 'structured json' if isinstance(body, dict) else 'raw/html'
        print(f'  HTTP {status}, {kind}: {str(body)[:200]}')
        self.findings['redform_error_shape'] = kind

        print('\n  -- 4 concurrent calls --')
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(
                lambda _: self.call(code, {'pageNo': 1, 'pageSize': 10}), range(4)))
        for i, (elapsed, status, body) in enumerate(results):
            outer = body.get('code') if isinstance(body, dict) else 'non-json'
            print(f'  #{i + 1} {elapsed:6.2f}s HTTP {status} code={outer}')
        serialised = max(r[0] for r in results) > 2 * statistics.median(times or [1])
        print(f'  {"serialised (one session behind it?)" if serialised else "parallel"}')
        self.findings['redform_concurrency'] = 'serialised' if serialised else 'parallel'

    def phase_ratelimit(self, burst=30, pause=0.0):
        """Their Q5 answer was 待回复. Find the working number ourselves."""
        self._require_creds()
        print(f'== ratelimit (read-only, burst={burst}) ==')
        code = CODES['red_form_query']
        first_reject = None
        for i in range(burst):
            elapsed, status, body = self.call(code, {'pageNo': 1, 'pageSize': 1})
            outer = body.get('code') if isinstance(body, dict) else 'non-json'
            throttled = status == 429 or 'limit' in str(body).lower() or '频' in str(body)
            print(f'  #{i + 1:3} {elapsed:6.2f}s HTTP {status} code={outer}'
                  f'{"  <-- THROTTLED" if throttled else ""}')
            if throttled and first_reject is None:
                first_reject = i + 1
                break
            if pause:
                time.sleep(pause)
        self.findings['rate_limit_first_reject'] = first_reject
        print(f'\n  {"throttled after " + str(first_reject) if first_reject else "no throttling in " + str(burst)} calls')
        print('  (sandbox enforcement, not a contractual limit -- still ask for that)')

    # --- phase 3: writes ---------------------------------------------------

    def phase_margin(self):
        """Q1: they said 都不支持差额发票, yet cezslx_dm (差额征收类型代码) is in the spec.

        Find out whether the field is rejected, ignored, or honoured.
        """
        if not self.allow_writes:
            sys.exit('phase issues a document: re-run with --allow-writes')
        self._require_creds()
        print('== margin / 差额发票 (WRITES) ==')
        code = CODES['invoice_issue']
        payload = {
            'fpqqlsh': f'PROBE{env.now_timestamp()}',
            'nsrsbh': self.tax_no,
            'cezslx_dm': '01',  # 差额征收类型代码, per the v1.8.2 field table
            'kplx': '0',
            # NOTE: fill the remaining mandatory issue fields from v1.8.4 §2.1.1
            # before running; this is deliberately incomplete so a stray run
            # cannot mint a real fapiao.
        }
        elapsed, status, body = self.call(code, payload)
        print(f'  HTTP {status} in {elapsed:.2f}s')
        print(f'  {json.dumps(body, ensure_ascii=False)[:600] if isinstance(body, dict) else str(body)[:600]}')
        print('\n  read the rejection: "unknown field" means silently ignored,')
        print('  an explicit 差额 error means recognised-but-disabled')
        self.findings['margin'] = body if isinstance(body, dict) else str(body)[:300]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('phase', choices=['envelope', 'auth', 'keyvariant', 'redform',
                                          'ratelimit', 'margin', 'all'])
    parser.add_argument('--host', choices=list(HOSTS), default='test')
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('--burst', type=int, default=30)
    parser.add_argument('--allow-writes', action='store_true')
    parser.add_argument('--i-mean-production', action='store_true')
    parser.add_argument('--report', help='write findings as json to this path')
    args = parser.parse_args()

    probe = Probe(args)
    print(f'host: {probe.base}\n')

    if args.phase == 'all':
        if probe.phase_envelope() and probe.phase_auth():
            probe.phase_redform()
            probe.phase_ratelimit(burst=args.burst)
    else:
        getattr(probe, f'phase_{args.phase}')(
            **({'burst': args.burst} if args.phase == 'ratelimit' else {}))

    if args.report:
        with open(args.report, 'w') as fh:
            json.dump(probe.findings, fh, ensure_ascii=False, indent=2)
        print(f'\nfindings -> {args.report}')


if __name__ == '__main__':
    main()

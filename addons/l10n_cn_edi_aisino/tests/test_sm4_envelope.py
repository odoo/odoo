# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Standalone unit tests for the Aisino SM4/HMAC envelope.

Run without Odoo:  python3 -m pytest addons/l10n_cn_edi_aisino/tests/test_sm4_envelope.py -v
"""
import os
import sys

import pytest

# Make the module importable without booting Odoo.
_MODULE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _MODULE_ROOT not in sys.path:
    sys.path.insert(0, _MODULE_ROOT)

from crypto import sm4_envelope as env  # noqa: E402

IDENTITY = 'b1492023dcd5368e'   # 授权码 (16-char)
PLATFORM = '101000'             # 组织编码 (6-digit)
TAX_NO = '91440606MA41111111'   # 税号
TS = '20231014180655'


# --- key derivation ---------------------------------------------------------

def test_sm4_key_is_middle_16_of_md5():
    """Key = the 16 hex CHARACTERS at [8:24] as UTF-8 bytes (16 bytes), NOT hex-decoded."""
    import hashlib
    md5hex = hashlib.md5((IDENTITY + PLATFORM + TS).encode()).hexdigest()
    key = env.derive_sm4_key(IDENTITY, PLATFORM, TS)
    assert key == md5hex[8:24].encode('utf-8')
    assert len(key) == 16  # 16 bytes = 128 bits (SM4 requirement)
    # not the first 16 chars, and not hex-decoded (which would be 8 bytes)
    assert key != md5hex[:16].encode('utf-8')
    assert key != bytes.fromhex(md5hex[8:24])


def test_access_token_is_base64_of_org_tax_ts():
    import base64
    expected = base64.b64encode((PLATFORM + TAX_NO + TS).encode()).decode()
    assert env.make_access_token(PLATFORM, TAX_NO, TS) == expected
    # and the timestamp is recoverable (last 14 chars of the b64 payload)
    assert env.timestamp_from_access_token(expected) == TS


# --- SM4 primitive ----------------------------------------------------------

def test_sm4_known_vector_single_block():
    """GB/T 32907-2016 example vector: key == plaintext == 0123...3210."""
    block = bytes.fromhex('0123456789abcdeffedcba9876543210')
    ct = env.sm4_encrypt(block, block)
    # PKCS5 always appends a full block of padding to a 16-byte input, so the
    # vector is the first block and the second one is the padding.
    assert ct[:16].hex() == '681edf34d206965e86b3e94f536e4246'
    assert len(ct) == 32
    assert env.sm4_decrypt(ct, block) == block


def test_sm4_roundtrip_with_padding():
    key = env.derive_sm4_key(IDENTITY, PLATFORM, TS)
    for length in (1, 15, 16, 17, 100, 4096):
        data = bytes(range(length % 256)) * (length // 256 + 1)
        data = data[:length]
        assert env.sm4_decrypt(env.sm4_encrypt(data, key), key) == data


# --- HMAC (doc known vector) -----------------------------------------------

def test_hmac_matches_doc_vector():
    """Doc 6.2: HMACSHA256('航天信息股份有限公司', key='12345678') -> BB2D...F625."""
    key = b'12345678'
    # sign() hashes the concatenation of the six envelope fields, so feed the
    # doc's message in as one of them and leave the rest empty.
    assert env.sign(
        interface_code='航天信息股份有限公司', zip_code='', encrypt_code='',
        access_token='', datagram='', signtype='', key=key,
    ) == 'BB2DBF98C94988269586CBDF83A5AABC8F65ABBCA9A931B11DAFFDC6A3D0F625'
    # and the concatenation order is the one the vendor signs
    assert env.sign('a', 'b', 'c', 'd', 'e', 'f', key) == \
        env.sign('abcdef', '', '', '', '', '', key)


# --- full envelope round-trip (all zipCode variants) ------------------------

@pytest.mark.parametrize('zip_code', ['0', '1', '2'])
def test_envelope_roundtrip(zip_code):
    payload = {'fpqqlsh': 'ABC123', 'nsrsbh': TAX_NO, '金额': 1234.56, '备注': '中文'}
    req = env.build_request('ele.encrypt.invoiceIssue', payload, IDENTITY, PLATFORM, TAX_NO,
                            timestamp=TS, zip_code=zip_code)
    assert req['zipCode'] == zip_code
    assert req['encryptCode'] == '1'
    assert req['signtype'] == 'HMacSHA256'
    # simulate the server side: verify + decrypt
    inner = env.verify_and_decrypt(dict(req, code='1000'), IDENTITY, PLATFORM)
    assert inner == payload


def test_autocompress_over_10k_uses_zip2():
    payload = {'blob': 'x' * 20000}
    req = env.build_request('ele.encrypt.invoiceIssue', payload, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
    assert req['zipCode'] == '2'
    assert env.verify_and_decrypt(dict(req, code='1000'), IDENTITY, PLATFORM) == payload


def test_small_payload_defaults_to_zip0():
    req = env.build_request('x', {'a': 1}, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
    assert req['zipCode'] == '0'


# --- signature tamper detection --------------------------------------------

def test_tampered_datagram_fails_signature():
    req = env.build_request('x', {'a': 1}, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
    req['datagram'] = req['datagram'][:-4] + ('AAAA' if not req['datagram'].endswith('AAAA') else 'BBBB')
    with pytest.raises(env.AisinoProtocolError):
        env.verify_and_decrypt(req, IDENTITY, PLATFORM)


def test_tampered_field_fails_signature():
    req = env.build_request('x', {'a': 1}, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
    req['access_token'] = 'AAAA' + req['access_token'][4:]
    with pytest.raises(env.AisinoProtocolError):
        env.verify_and_decrypt(req, IDENTITY, PLATFORM)


def test_wrong_key_fails_signature():
    req = env.build_request('x', {'a': 1}, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
    with pytest.raises(env.AisinoProtocolError):
        env.verify_and_decrypt(req, 'wrongidentity000000', PLATFORM)


# --- outer code handling ----------------------------------------------------

def test_outer_code_failure_raises():
    resp = env.build_response('x', {}, IDENTITY, PLATFORM, timestamp=TS, code='9994', msg='fpqqlsh duplicate')
    with pytest.raises(env.AisinoProtocolError) as ei:
        env.verify_and_decrypt(resp, IDENTITY, PLATFORM)
    assert ei.value.code == '9994'


def test_success_returns_inner_dict():
    resp = env.build_response('ele.encrypt.queryResult', {'code': '1002', 'message': '开票中'},
                              IDENTITY, PLATFORM, timestamp=TS)
    inner = env.verify_and_decrypt(resp, IDENTITY, PLATFORM)
    assert inner == {'code': '1002', 'message': '开票中'}


# --- SM4 primitive ----------------------------------------------------------

def test_sm4_fallback_agrees_with_openssl():
    """Skipped where cryptography has no SM4 — which is exactly why the fallback exists."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    from crypto import sm4_pure

    if not env.HAS_NATIVE_SM4:
        pytest.skip('cryptography built without SM4')
    key = b'0123456789abcdef'
    data = b'A' * 32
    enc = Cipher(algorithms.SM4(key), modes.ECB()).encryptor()
    assert sm4_pure.encrypt_ecb(data, key) == enc.update(data) + enc.finalize()


def test_envelope_round_trips_without_native_sm4(monkeypatch):
    """The whole envelope must work on a host whose OpenSSL lacks SM4."""
    monkeypatch.setattr(env, 'HAS_NATIVE_SM4', False)
    payload = {'probe': 'ok', '中文': '测试', 'n': 1234.56}
    for zip_code in ('0', '1', '2'):
        request = env.build_request('x', payload, IDENTITY, PLATFORM, TAX_NO,
                                    timestamp=TS, zip_code=zip_code)
        assert env.verify_and_decrypt(dict(request, code='1000'), IDENTITY, PLATFORM) == payload

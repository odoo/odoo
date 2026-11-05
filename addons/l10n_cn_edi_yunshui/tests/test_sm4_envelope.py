# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import gzip
import hashlib
from unittest.mock import patch

from odoo.tests import BaseCase, tagged

from odoo.addons.l10n_cn_edi_yunshui.crypto import sm4_envelope as env

IDENTITY = 'b1492023dcd5368e'  # 授权码 (16-char)
PLATFORM = '101000'  # 组织编码 (6-digit)
TAX_NO = '91440606MA41111111'  # 税号
TS = '20231014180655'


def _signed_response(datagram, zip_code='0'):
    """Return a response correctly signed over an arbitrary datagram."""
    response = env.build_response('x', {}, IDENTITY, PLATFORM, timestamp=TS, zip_code=zip_code)
    response['datagram'] = datagram
    key = env.derive_sm4_key(IDENTITY, PLATFORM, TS)
    response['signature'] = env.sign(*(response[field] for field in env.SIGNED_FIELDS), key)
    return response


def _encrypted_hex(data):
    return env.sm4_encrypt(data, env.derive_sm4_key(IDENTITY, PLATFORM, TS)).hex().encode('ascii')


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSm4Envelope(BaseCase):

    def test_sm4_key_is_middle_16_of_md5(self):
        """Key = the 16 hex characters at [8:24] as UTF-8 bytes, not hex-decoded (Java demo)."""
        md5hex = hashlib.md5((IDENTITY + PLATFORM + TS).encode()).hexdigest()
        key = env.derive_sm4_key(IDENTITY, PLATFORM, TS)
        self.assertEqual(key, md5hex[8:24].encode('utf-8'))
        self.assertEqual(len(key), 16)

    def test_access_token_is_base64_of_org_tax_ts(self):
        expected = base64.b64encode((PLATFORM + TAX_NO + TS).encode()).decode()
        self.assertEqual(env.make_access_token(PLATFORM, TAX_NO, TS), expected)
        self.assertEqual(env.timestamp_from_access_token(expected), TS)

    def test_sm4_known_vector_single_block(self):
        """GB/T 32907-2016 example vector: key == plaintext == 0123...3210."""
        block = bytes.fromhex('0123456789abcdeffedcba9876543210')
        ciphertext = env.sm4_encrypt(block, block)
        # PKCS5 appends a full block of padding to a 16-byte input: the vector is the first block.
        self.assertEqual(ciphertext[:16].hex(), '681edf34d206965e86b3e94f536e4246')
        self.assertEqual(len(ciphertext), 32)
        self.assertEqual(env.sm4_decrypt(ciphertext, block), block)

    def test_sm4_roundtrip_with_padding(self):
        key = env.derive_sm4_key(IDENTITY, PLATFORM, TS)
        for length in (1, 15, 16, 17, 100, 4096):
            data = (bytes(range(length % 256)) * (length // 256 + 1))[:length]
            self.assertEqual(env.sm4_decrypt(env.sm4_encrypt(data, key), key), data)

    def test_hmac_matches_doc_vector(self):
        """Doc 6.2: HMACSHA256('航天信息股份有限公司', key='12345678') -> BB2D...F625."""
        key = b'12345678'
        self.assertEqual(
            env.sign(
                interface_code='航天信息股份有限公司', zip_code='', encrypt_code='',
                access_token='', datagram='', signtype='', key=key,
            ),
            'BB2DBF98C94988269586CBDF83A5AABC8F65ABBCA9A931B11DAFFDC6A3D0F625',
        )
        self.assertEqual(env.sign('a', 'b', 'c', 'd', 'e', 'f', key), env.sign('abcdef', '', '', '', '', '', key))

    def test_envelope_roundtrip(self):
        payload = {'fpqqlsh': 'ABC123', 'nsrsbh': TAX_NO, '金额': 1234.56, '备注': '中文'}
        request = env.build_request('ele.encrypt.invoiceIssue', payload, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
        self.assertEqual(
            (request['zipCode'], request['encryptCode'], request['signtype']),
            ('0', '1', 'HMacSHA256'),
        )
        self.assertEqual(env.verify_and_decrypt(dict(request, code='1000'), IDENTITY, PLATFORM), payload)

    def test_datagram_carries_the_ciphertext_as_hex(self):
        """The gateway decrypts base64(hex(sm4(json))), as the Java demo's hutool encryptHex does."""
        key = env.derive_sm4_key(IDENTITY, PLATFORM, TS)
        request = env.build_request('x', {'a': 1}, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
        carried = base64.b64decode(request['datagram']).decode('ascii')
        self.assertTrue(all(char in '0123456789abcdef' for char in carried))
        self.assertEqual(env.sm4_decrypt(bytes.fromhex(carried), key), b'{"a":1}')

    def test_compressed_responses_are_decoded(self):
        payload = {'fpqqlsh': 'ABC123', '备注': '中文'}
        for zip_code in ('0', '1', '2'):
            with self.subTest(zip_code=zip_code):
                response = env.build_response('x', payload, IDENTITY, PLATFORM, timestamp=TS, zip_code=zip_code)
                self.assertEqual(env.verify_and_decrypt(response, IDENTITY, PLATFORM), payload)

    def test_large_payload_is_still_sent_uncompressed(self):
        payload = {'blob': 'x' * 20000}
        request = env.build_request('ele.encrypt.invoiceIssue', payload, IDENTITY, PLATFORM, TAX_NO, timestamp=TS)
        self.assertEqual(request['zipCode'], '0')
        self.assertEqual(env.verify_and_decrypt(dict(request, code='1000'), IDENTITY, PLATFORM), payload)

    def test_response_signature_is_ignored(self):
        """Responses echo the request's signature, which Yunshui says to ignore."""
        response = env.build_response('x', {'a': 1}, IDENTITY, PLATFORM, timestamp=TS)
        response['signature'] = 'BAD'
        self.assertEqual(env.verify_and_decrypt(response, IDENTITY, PLATFORM), {'a': 1})

    def test_outer_code_failure_raises(self):
        response = env.build_response('x', {}, IDENTITY, PLATFORM, timestamp=TS, code='9994', msg='fpqqlsh duplicate')
        with self.assertRaises(env.YunshuiProtocolError) as error:
            env.verify_and_decrypt(response, IDENTITY, PLATFORM)
        self.assertEqual(error.exception.code, '9994')

    def test_outer_failure_is_read_before_the_empty_datagram(self):
        """On failure the datagram is an empty node (spec 1.2)."""
        response = {'code': '9995', 'msg': '验签未通过', 'datagram': '', 'signature': 'echo'}
        with self.assertRaises(env.YunshuiProtocolError) as error:
            env.verify_and_decrypt(response, IDENTITY, PLATFORM)
        self.assertEqual(error.exception.code, '9995')
        with self.assertRaises(env.YunshuiProtocolError):
            env.verify_and_decrypt({}, IDENTITY, PLATFORM)

    def test_unreadable_envelopes_are_malformed(self):
        missing = {}
        for field in ('access_token', 'datagram', 'zipCode'):
            missing[field] = env.build_response('x', {'a': 1}, IDENTITY, PLATFORM, timestamp=TS)
            del missing[field][field]
        bad_token = env.build_response('x', {'a': 1}, IDENTITY, PLATFORM, timestamp=TS)
        bad_token['access_token'] = 'abc'
        raw_ciphertext = env.sm4_encrypt(b'{"a":1}', env.derive_sm4_key(IDENTITY, PLATFORM, TS))
        truncated_gzip = gzip.compress(_encrypted_hex(b'{"a":1}'))[:-12]
        cases = {
            **{f'missing {field}': response for field, response in missing.items()},
            'not an object': ['1000'],
            'bad access token': bad_token,
            'bad base64': _signed_response('not base64!'),
            'bad hex': _signed_response(base64.b64encode(b'zz-not-hex').decode()),
            'hex, not a ciphertext': _signed_response(base64.b64encode(b'abcd').decode()),
            'decrypts, not JSON': _signed_response(base64.b64encode(_encrypted_hex(b'{"a":')).decode()),
            'raw ciphertext': _signed_response(base64.b64encode(raw_ciphertext).decode()),
            'truncated gzip': _signed_response(base64.b64encode(truncated_gzip).decode(), zip_code='1'),
        }
        for case, response in cases.items():
            with self.subTest(case=case), self.assertRaises(env.MalformedEnvelope):
                env.verify_and_decrypt(response, IDENTITY, PLATFORM)

    def test_oversized_datagram_is_rejected_before_decoding(self):
        with patch.object(env, 'MAX_DATAGRAM_LENGTH', 64), self.assertRaisesRegex(env.MalformedEnvelope, 'too large'):
            env.verify_and_decrypt(_signed_response('A' * 65), IDENTITY, PLATFORM)

    def test_decompression_is_capped(self):
        for zip_code in ('1', '2'):
            response = env.build_response('x', {'blob': 'x' * 4096}, IDENTITY, PLATFORM, timestamp=TS, zip_code=zip_code)
            with self.subTest(zip_code=zip_code), patch.object(env, 'MAX_DECOMPRESSED_BYTES', 1024), \
                    self.assertRaisesRegex(env.MalformedEnvelope, 'too large'):
                env.verify_and_decrypt(response, IDENTITY, PLATFORM)

    def test_success_returns_inner_dict(self):
        response = env.build_response(
            'ele.encrypt.queryResult', {'code': '1002', 'message': '开票中'}, IDENTITY, PLATFORM, timestamp=TS,
        )
        self.assertEqual(env.verify_and_decrypt(response, IDENTITY, PLATFORM), {'code': '1002', 'message': '开票中'})

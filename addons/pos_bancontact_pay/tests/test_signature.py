import base64
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from freezegun import freeze_time
from requests import Response

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.controllers.signature import BancontactSignatureValidation
from odoo.addons.pos_bancontact_pay.errors.exceptions import BancontactSignatureValidationError


@tagged("post_install", "-at_install")
class TestSignature(CommonPosTest, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.utils = BancontactTestUtils()

    # ----- _extract_jws_parts ----- #
    def test_extract_jws_parts_missing_signature(self):
        request = MockRequest()
        validation = BancontactSignatureValidation(request)
        with self.bancontact_signature_raise("Missing Signature header"):
            validation._extract_jws_parts()

    def test_extract_jws_parts_malformed_signature(self):
        request = MockRequest(headers={"Signature": "not-a-valid-jws"})
        validation = BancontactSignatureValidation(request)
        with self.bancontact_signature_raise("Malformed Signature format."):
            validation._extract_jws_parts()

    def test_extract_jws_parts_unable_to_decode_protected_header(self):
        signature = "invalid-base64..signature"
        request = MockRequest(headers={"Signature": signature})
        validation = BancontactSignatureValidation(request)
        with self.bancontact_signature_raise("Unable to decode or parse protected header."):
            validation._extract_jws_parts()

    def test_extract_jws_parts_unable_to_parse_protected_header(self):
        protected_b64 = base64.urlsafe_b64encode(b"not-json").decode().rstrip("=")
        signature = f"{protected_b64}..signature"
        request = MockRequest(headers={"Signature": signature})
        validation = BancontactSignatureValidation(request)
        with self.bancontact_signature_raise("Unable to decode or parse protected header."):
            validation._extract_jws_parts()

    def test_extract_jws_parts_unable_to_find_kid_in_protected_header(self):
        protected = {"alg": "ES256"}
        protected_b64 = base64.urlsafe_b64encode(json.dumps(protected).encode()).decode().rstrip("=")
        signature = f"{protected_b64}..signature"
        request = MockRequest(headers={"Signature": signature})
        validation = BancontactSignatureValidation(request)
        with self.bancontact_signature_raise("Unable to decode or parse protected header."):
            validation._extract_jws_parts()

    def test_extract_jws_parts_valid(self):
        kid = "dummy-kid"
        protected = {"alg": "ES256", "kid": kid}
        protected_b64 = base64.urlsafe_b64encode(json.dumps(protected).encode()).decode().rstrip("=")
        signature_b64 = "signature"
        signature = f"{protected_b64}..{signature_b64}"
        request = MockRequest(headers={"Signature": signature})
        validation = BancontactSignatureValidation(request)
        extracted_protected_b64, extracted_signature_b64, extracted_kid, extracted_protected = validation._extract_jws_parts()

        self.assertEqual(extracted_protected_b64, protected_b64)
        self.assertEqual(extracted_signature_b64, signature_b64)
        self.assertEqual(extracted_kid, kid)
        self.assertEqual(extracted_protected, protected)

    # ----- _get_jwk_by_kid ----- #
    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_cache(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        cache = {
            "timestamp": "2026-02-12T06:00:00+00:00",
            "jwks": [jwk],
        }
        with self.mock_jwk_fetch([jwk], called=False, cache=cache) as get_cache:
            validation = BancontactSignatureValidation(MockRequest())
            result = validation._get_jwk_by_kid(kid)
            self.assertEqual(result, jwk)
        self.assertEqual(get_cache(), cache)

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_no_cache(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        with self.mock_jwk_fetch([jwk]) as get_cache:
            validation = BancontactSignatureValidation(MockRequest())
            result = validation._get_jwk_by_kid(kid)
            self.assertEqual(result, jwk)
        self.assertEqual(get_cache(), {
            "timestamp": "2026-02-12T12:00:00+00:00",
            "jwks": [jwk],
        })

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_expired_cache(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        cache = {
            "timestamp": "2026-02-11T12:00:00+00:00",
            "jwks": [jwk],
        }
        with self.mock_jwk_fetch([jwk], cache=cache) as get_cache:
            validation = BancontactSignatureValidation(MockRequest())
            result = validation._get_jwk_by_kid(kid)
            self.assertEqual(result, jwk)
        self.assertEqual(get_cache(), {
            "timestamp": "2026-02-12T12:00:00+00:00",
            "jwks": [jwk],
        })

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_kid_not_found_in_cache(self):
        other_kid = "other-kid"
        _other_private_key, other_public_key = self.utils.generate_keypair_ES256()
        other_jwk = self.utils.create_jwk_ES256(other_public_key, other_kid)
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        cache = {
            "timestamp": "2026-02-12T06:00:00+00:00",
            "jwks": [other_jwk],
        }
        with self.mock_jwk_fetch([jwk], cache=cache) as get_cache:
            validation = BancontactSignatureValidation(MockRequest())
            result = validation._get_jwk_by_kid(kid)
            self.assertEqual(result, jwk)
        self.assertEqual(get_cache(), {
            "timestamp": "2026-02-12T12:00:00+00:00",
            "jwks": [jwk],
        })

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_kid_in_cache_not_sig(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        cache = {
            "timestamp": "2026-02-12T06:00:00+00:00",
            "jwks": [{**jwk, "use": "enc"}],
        }
        with self.mock_jwk_fetch([jwk], cache=cache) as get_cache:
            validation = BancontactSignatureValidation(MockRequest())
            result = validation._get_jwk_by_kid(kid)
            self.assertEqual(result, jwk)
        self.assertEqual(get_cache(), {
            "timestamp": "2026-02-12T12:00:00+00:00",
            "jwks": [jwk],
        })

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_kid_in_cache_use_none(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        jwk_no_use = {**jwk}
        jwk_no_use.pop("use")
        cache = {
            "timestamp": "2026-02-12T06:00:00+00:00",
            "jwks": [jwk_no_use],
        }
        with self.mock_jwk_fetch([jwk], called=False, cache=cache) as get_cache:
            validation = BancontactSignatureValidation(MockRequest())
            result = validation._get_jwk_by_kid(kid)
            self.assertEqual(result, jwk_no_use)
        self.assertEqual(get_cache(), cache)

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_fetched_kid_not_found(self):
        other_kid = "other-kid"
        _other_private_key, other_public_key = self.utils.generate_keypair_ES256()
        other_jwk = self.utils.create_jwk_ES256(other_public_key, other_kid)
        kid = "dummy-kid"
        with self.mock_jwk_fetch([other_jwk]) as get_cache, self.bancontact_signature_raise(f"JWK with kid {kid} not found after JWKS refresh"):
            validation = BancontactSignatureValidation(MockRequest())
            validation._get_jwk_by_kid(kid)
        self.assertEqual(get_cache(), None)

    @freeze_time("2026-02-12 12:00:00")
    def test_get_jwk_by_kid_fetched_kid_not_sig(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        jwk.update({"use": "enc"})
        with self.mock_jwk_fetch([jwk]) as get_cache, self.bancontact_signature_raise(f"JWK with kid {kid} is not for signature use"):
            validation = BancontactSignatureValidation(MockRequest())
            validation._get_jwk_by_kid(kid)
        self.assertEqual(get_cache(), None)

    # ----- _verify_jws_signature ----- #
    def test_verify_jws_signature_unsupported_algo(self):
        kid = "dummy-kid"
        _private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)
        jwk.update({"alg": "ES384"})

        payload = b"test payload"
        validation = BancontactSignatureValidation(MockRequest(data=payload))

        with self.bancontact_signature_raise("Unsupported JWK algorithm: ES384"):
            validation._verify_jws_signature(jwk, "87654321", "12345678")

    def test_verify_jws_signature_es256_success(self):
        kid = "dummy-kid"
        private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)

        payload = b"test payload"
        header = self.utils.create_protected_header(kid, "https://example.com/webhook", "dummy-ppid")
        signature = self.utils.sign_jws_ES256(private_key, header, payload)

        validation = BancontactSignatureValidation(MockRequest(data=payload))
        protected_b64 = signature.split("..")[0]
        signature_b64 = signature.split("..")[1]
        validation._verify_jws_signature(jwk, protected_b64, signature_b64)

    def test_verify_jws_signature_es256_failed(self):
        kid = "dummy-kid"
        private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)

        payload = b"test payload"
        header = self.utils.create_protected_header(kid, "https://example.com/webhook", "dummy-ppid")
        signature = self.utils.sign_jws_ES256(private_key, header, payload)

        validation = BancontactSignatureValidation(MockRequest(data=payload))
        protected_b64 = signature.split("..")[0]
        signature_b64 = signature.split("..")[1]

        # Tamper with the payload to cause signature verification failure
        tampered_payload = b"tampered payload"
        validation.request.data = tampered_payload

        with self.bancontact_signature_raise("ECDSA signature verification failed."):
            validation._verify_jws_signature(jwk, protected_b64, signature_b64)

    def test_verify_jws_signature_rs256_success(self):
        kid = "dummy-kid"
        private_key, public_key = self.utils.generate_keypair_RS256()
        jwk = self.utils.create_jwk_RS256(public_key, kid)

        payload = b"test payload"
        header = self.utils.create_protected_header(kid, "https://example.com/webhook", "dummy-ppid")
        signature = self.utils.sign_jws_RS256(private_key, header, payload)

        validation = BancontactSignatureValidation(MockRequest(data=payload))
        protected_b64 = signature.split("..")[0]
        signature_b64 = signature.split("..")[1]
        validation._verify_jws_signature(jwk, protected_b64, signature_b64)

    def test_verify_jws_signature_rs256_failed(self):
        kid = "dummy-kid"
        private_key, public_key = self.utils.generate_keypair_RS256()
        jwk = self.utils.create_jwk_RS256(public_key, kid)

        payload = b"test payload"
        header = self.utils.create_protected_header(kid, "https://example.com/webhook", "dummy-ppid")
        signature = self.utils.sign_jws_RS256(private_key, header, payload)

        validation = BancontactSignatureValidation(MockRequest(data=payload))
        protected_b64 = signature.split("..")[0]
        signature_b64 = signature.split("..")[1]

        # Tamper with the payload to cause signature verification failure
        tampered_payload = b"tampered payload"
        validation.request.data = tampered_payload

        with self.bancontact_signature_raise("RSA signature verification failed."):
            validation._verify_jws_signature(jwk, protected_b64, signature_b64)

    # ----- _validate_critical_headers ----- #
    @freeze_time("2026-02-12 12:00:00")
    def test_validate_critical_headers_missing_unexpected_crit(self):
        protected = {
            "crit": [const.IAT_KEY, const.PATH_KEY, const.SUB_KEY, "unexpected-crit"],
            const.IAT_KEY: "2026-02-12T12:00:00.000Z",
            const.PATH_KEY: "https://example.com/webhook",
            const.SUB_KEY: "dummy-ppid",
            "unexpected-crit": "value",
        }
        validation = BancontactSignatureValidation(MockRequest())
        missing = {const.ISS_KEY, const.JTI_KEY}
        unexpected = {"unexpected-crit"}
        with self.bancontact_signature_raise(f"Invalid crit header: missing {missing}, unexpected {unexpected}"):
            validation._validate_critical_headers(protected)

    @freeze_time("2026-02-12 12:00:00")
    def test_validate_critical_headers_wrong_iss(self):
        protected = {
            "crit": [const.ISS_KEY, const.IAT_KEY, const.JTI_KEY, const.PATH_KEY, const.SUB_KEY],
            const.ISS_KEY: "dummy",
            const.IAT_KEY: "2026-02-12T12:00:00.000Z",
            const.JTI_KEY: "unique-jti-12345",
            const.PATH_KEY: "https://example.com/webhook",
            const.SUB_KEY: "dummy-ppid",
        }
        validation = BancontactSignatureValidation(MockRequest())
        with self.bancontact_signature_raise("Invalid issuer: dummy"):
            validation._validate_critical_headers(protected)

        protected.pop(const.ISS_KEY)
        with self.bancontact_signature_raise(f"Missing required protected header(s): ['{const.ISS_KEY}']"):
            validation._validate_critical_headers(protected)

    @freeze_time("2026-02-12 12:00:00")
    def test_validate_critical_headers_wrong_iat(self):
        protected = {
            "crit": [const.ISS_KEY, const.IAT_KEY, const.JTI_KEY, const.PATH_KEY, const.SUB_KEY],
            const.ISS_KEY: const.ISS_VALUE,
            const.IAT_KEY: "2026-02-12T11:00:00.000Z",
            const.JTI_KEY: "unique-jti-12345",
            const.PATH_KEY: "https://example.com/webhook",
            const.SUB_KEY: "dummy-ppid",
        }
        validation = BancontactSignatureValidation(MockRequest())
        with self.bancontact_signature_raise(f"Invalid iat: outside allowed skew ({const.MAX_SKEW_SECONDS}s)"):
            validation._validate_critical_headers(protected)

        protected.update({const.IAT_KEY: "2026-02-12T13:00:00.000Z"})
        with self.bancontact_signature_raise(f"Invalid iat: outside allowed skew ({const.MAX_SKEW_SECONDS}s)"):
            validation._validate_critical_headers(protected)

        protected.update({const.IAT_KEY: "invalid-format"})
        with self.bancontact_signature_raise("Invalid iat format: invalid-format"):
            validation._validate_critical_headers(protected)

        protected.pop(const.IAT_KEY)
        with self.bancontact_signature_raise(f"Missing required protected header(s): ['{const.IAT_KEY}']"):
            validation._validate_critical_headers(protected)

    @freeze_time("2026-02-12 12:00:00")
    def test_validate_critical_headers_wrong_path(self):
        protected = {
            "crit": [const.ISS_KEY, const.IAT_KEY, const.JTI_KEY, const.PATH_KEY, const.SUB_KEY],
            const.ISS_KEY: const.ISS_VALUE,
            const.IAT_KEY: "2026-02-12T12:00:00.000Z",
            const.JTI_KEY: "unique-jti-12345",
            const.PATH_KEY: "https://example.com/error",
            const.SUB_KEY: "dummy-ppid",
        }
        validation = BancontactSignatureValidation(MockRequest())
        with self.bancontact_signature_raise("Path mismatch: https://example.com/error != https://example.com/webhook"):
            validation._validate_critical_headers(protected)

    @freeze_time("2026-02-12 12:00:00")
    def test_validate_critical_headers_success(self):
        protected = {
            "crit": [const.ISS_KEY, const.IAT_KEY, const.JTI_KEY, const.PATH_KEY, const.SUB_KEY],
            const.ISS_KEY: const.ISS_VALUE,
            const.IAT_KEY: "2026-02-12T12:00:00.000Z",
            const.JTI_KEY: "unique-jti-12345",
            const.PATH_KEY: "http://example.com/webhook",  # Allow http vs https mismatch
            const.SUB_KEY: "save-subject",
        }
        validation = BancontactSignatureValidation(MockRequest())
        validation._validate_critical_headers(protected)
        self.assertEqual(validation.subject, "save-subject")

    # ----- verify_subject ----- #
    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.signature")
    def test_verify_subject_mismatch(self):
        validation = BancontactSignatureValidation(MockRequest())
        validation.subject = "dummy-ppid"
        validation.verify_subject("dummy-ppid")

        validation.subject = "wrong-ppid"
        with self.bancontact_signature_raise("Invalid subject: wrong-ppid"):
            validation.verify_subject("dummy-ppid")

        validation.test_mode = True
        validation.verify_subject("dummy-ppid")  # Should not raise in test mode

    # ----- verify_signature ----- #
    @mute_logger("odoo.addons.pos_bancontact_pay.controllers.signature")
    @freeze_time("2026-02-12 12:00:00")
    def test_verify_signature_invalid_signature(self):
        kid = "dummy-kid"
        private_key, public_key = self.utils.generate_keypair_ES256()
        jwk = self.utils.create_jwk_ES256(public_key, kid)

        payload = b"dummy payload"
        header = self.utils.create_protected_header(kid, "https://example.com/webhook", "dummy-ppid")
        signature = self.utils.sign_jws_ES256(private_key, header, payload)

        cache = {
            "timestamp": "2026-02-12T06:00:00+00:00",
            "jwks": [jwk],
        }
        with self.mock_jwk_fetch([jwk], called=False, cache=cache) as get_cache:
            validation = BancontactSignatureValidation(MockRequest(data=payload, headers={"Signature": signature}))
            validation.verify_signature()
        self.assertEqual(get_cache(), cache)

        tampered_payload = b"tampered payload"
        validation.request.data = tampered_payload
        with self.mock_jwk_fetch([jwk], called=False, cache=cache) as get_cache, \
            self.bancontact_signature_raise("ECDSA signature verification failed."):
            validation.verify_signature()
        self.assertEqual(get_cache(), cache)

        validation.test_mode = True
        with self.mock_jwk_fetch([jwk], called=False, cache=cache) as get_cache:
            validation.verify_signature()  # Should not raise in test mode
        self.assertEqual(get_cache(), cache)

    # ----- Context Manager ----- #
    @contextmanager
    def bancontact_signature_raise(self, msg):
        with self.assertRaises(BancontactSignatureValidationError) as ctx:
            yield
        self.assertEqual(str(ctx.exception), msg)

    @contextmanager
    def mock_jwk_fetch(self, jwks, called=True, cache=None):
        memo = {}
        if cache:
            memo["pos_bancontact.jwk_cache"] = json.dumps(cache) if cache is not None else None

        def _set_str(key, value):
            nonlocal memo
            memo[key] = value

        def _get_str(key):
            return memo.get(key)

        mock_param = MagicMock()
        mock_param.set_str.side_effect = _set_str
        mock_param.get_str.side_effect = _get_str
        mock_param.sudo.return_value = mock_param

        mock_request = MagicMock()
        mock_request.env.__getitem__.return_value = mock_param

        with (
            patch("odoo.addons.pos_bancontact_pay.controllers.signature.requests.get") as mock_get,
            patch("odoo.addons.pos_bancontact_pay.controllers.signature.request", mock_request),
        ):
            mock_get.return_value = self.utils.create_jwks_response(jwks)
            yield lambda: json.loads(memo.get("pos_bancontact.jwk_cache")) if memo.get("pos_bancontact.jwk_cache") else None

            if called:
                mock_get.assert_called_once()
            else:
                mock_get.assert_not_called()


class MockRequest:
    def __init__(self, data=b"{}", headers={}, url="https://example.com/webhook"):
        self.data = data
        self.headers = headers
        self.url = url


class BancontactTestUtils:
    """Test utilities for Bancontact signature testing."""

    @staticmethod
    def b64url_encode(data: bytes) -> str:
        """Encode bytes to base64url without padding."""
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    @staticmethod
    def generate_keypair_ES256():
        """Generate EC P-256 key pair."""
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        return private_key, private_key.public_key()

    @staticmethod
    def generate_keypair_RS256():
        """Generate RSA 2048 key pair."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        return private_key, private_key.public_key()

    @classmethod
    def create_jwk_ES256(cls, public_key, kid):
        """Create JWK from EC public key."""
        public_numbers = public_key.public_numbers()
        return {
            "kty": "EC",
            "use": "sig",
            "alg": "ES256",
            "crv": "P-256",
            "x": cls.b64url_encode(public_numbers.x.to_bytes(32, "big")),
            "y": cls.b64url_encode(public_numbers.y.to_bytes(32, "big")),
            "kid": kid,
        }

    @classmethod
    def create_jwk_RS256(cls, public_key, kid):
        """Create JWK from RSA 256 public key."""
        public_numbers = public_key.public_numbers()
        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "n": cls.b64url_encode(public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")),
            "e": cls.b64url_encode(public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")),
            "kid": kid,
        }

    @classmethod
    def sign_jws_ES256(cls, private_key, protected_header: dict, payload: bytes) -> str:
        """Create detached JWS signature (protected..signature)."""
        protected_b64 = cls.b64url_encode(json.dumps(protected_header, separators=(",", ":")).encode())
        payload_b64 = cls.b64url_encode(payload)
        signing_input = f"{protected_b64}.{payload_b64}".encode()

        signature_der = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(signature_der)
        signature_raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        signature_b64 = cls.b64url_encode(signature_raw)

        return f"{protected_b64}..{signature_b64}"

    @classmethod
    def sign_jws_RS256(cls, private_key, protected_header: dict, payload: bytes) -> str:
        """Create detached JWS signature (protected..signature)."""
        protected_b64 = cls.b64url_encode(json.dumps(protected_header, separators=(",", ":")).encode())
        payload_b64 = cls.b64url_encode(payload)
        signing_input = f"{protected_b64}.{payload_b64}".encode()

        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        signature_b64 = cls.b64url_encode(signature)

        return f"{protected_b64}..{signature_b64}"

    @staticmethod
    def create_protected_header(kid: str, url: str, ppid: str, **overrides) -> dict:
        """Create valid protected header with optional overrides."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        header = {
            "alg": "ES256",
            "kid": kid,
            "crit": [
                const.ISS_KEY,
                const.IAT_KEY,
                const.JTI_KEY,
                const.PATH_KEY,
                const.SUB_KEY,
            ],
            const.ISS_KEY: const.ISS_VALUE,
            const.IAT_KEY: now,
            const.JTI_KEY: "unique-jti-12345",
            const.PATH_KEY: url,
            const.SUB_KEY: ppid,
        }
        header.update(overrides)
        return header

    @staticmethod
    def create_jwks_response(jwks: list) -> Response:
        """Create a mock Response object for JWKS endpoint."""
        response = Response()
        response.status_code = 200
        response._content = json.dumps({"keys": jwks}).encode()
        return response

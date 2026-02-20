import base64
import json
import logging
from binascii import Error as BinasciiError
from datetime import datetime, timedelta, UTC

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

from odoo.http import request

from odoo.addons.pos_bancontact_pay import const
from odoo.addons.pos_bancontact_pay.errors.exceptions import BancontactSignatureValidationError

_logger = logging.getLogger(__name__)


class BancontactSignatureValidation:
    def __init__(self, request, test_mode=False):
        self.request = request
        self.test_mode = test_mode
        self.bancontact_api_urls = const.API_URLS["preprod" if test_mode else "production"]

    def verify_signature(self):
        """Verify the JWS signature and mandatory protected headers of the request."""
        if self.test_mode:
            return

        try:
            protected_b64, signature_b64, kid, protected = self._extract_jws_parts()
            jwk = self._get_jwk_by_kid(kid)
            self._verify_jws_signature(jwk, protected_b64, signature_b64)
            self._validate_critical_headers(protected)
        except BancontactSignatureValidationError as e:
            _logger.warning("Bancontact signature verification failed:\n%s", e)
            raise

    def verify_subject(self, expected_subject):
        """Ensure the JWS subject matches the expected payment profile identifier."""
        if self.test_mode:
            return

        if self.subject != expected_subject:
            e = f"Invalid subject: {self.subject}"
            _logger.warning("Bancontact signature subject verification failed:\n%s", e)
            raise BancontactSignatureValidationError(e)

    # ----- Private Methods ----- #
    def _extract_jws_parts(self):
        """Parse the detached JWS from the Signature header and return its components."""
        # Get the 'Signature' header
        signature = self.request.headers.get("Signature")
        if not signature:
            raise BancontactSignatureValidationError("Missing Signature header")

        # The JWS is in the form: protected_b64..signature_b64 (note: payload is detached)
        try:
            protected_b64, _empty_playload_64, signature_b64 = signature.split(".")
        except (ValueError, AttributeError, TypeError) as e:
            raise BancontactSignatureValidationError("Malformed Signature format.") from e

        # Decode the protected header (JOSE header)
        try:
            protected_json = self._b64url_decode(protected_b64).decode("utf-8")
            protected = json.loads(protected_json)
            kid = protected["kid"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as e:
            raise BancontactSignatureValidationError("Unable to decode or parse protected header.") from e

        return protected_b64, signature_b64, kid, protected

    def _get_jwk_by_kid(self, kid):
        """Resolve the public JWK for a given key id (kid), using a short-lived cache."""
        now = datetime.now(UTC)
        cache_param = request.env["ir.config_parameter"].sudo().get_str("pos_bancontact.jwk_cache")
        cache = json.loads(cache_param) if cache_param else {}
        cache_jwks = cache.get("jwks", [])
        cache_timestamp = cache.get("timestamp", None)
        if cache_timestamp:
            cache_timestamp = datetime.fromisoformat(cache_timestamp)

        # Use cached JWKS if valid
        if (
            cache_jwks
            and cache_timestamp
            and (now - cache_timestamp) < timedelta(hours=const.JWKS_TTL)
        ):
            jwks = cache_jwks
        else:
            jwks = []

        def _build_jwks_by_kid(jwks):
            return {key["kid"]: key for key in jwks if "kid" in key}

        # Extract the JWK with the matching kid
        jwk_data = _build_jwks_by_kid(jwks).get(kid)
        if jwk_data and jwk_data.get("use", "sig") == "sig":
            return jwk_data

        # Fetch fresh JWKS from Bancontact if not found in cache
        jwks_url = self.bancontact_api_urls["jwks"]
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        jwks = response.json().get("keys", [])

        jwk_data = _build_jwks_by_kid(jwks).get(kid)
        if not jwk_data:
            raise BancontactSignatureValidationError(f"JWK with kid {kid} not found after JWKS refresh")
        if jwk_data.get("use", "sig") != "sig":
            raise BancontactSignatureValidationError(f"JWK with kid {kid} is not for signature use")

        request.env["ir.config_parameter"].sudo().set_str(
            "pos_bancontact.jwk_cache",
            json.dumps(
                {
                    "timestamp": now.isoformat(),
                    "jwks": jwks,
                },
            ),
        )
        return jwk_data

    def _verify_jws_signature(self, jwk, protected_b64, signature_b64):
        """Verify the request payload against the provided JWS signature and JWK."""
        # Rebuild the signed input: base64url(protected header) + "." + base64url(payload)
        payload_b64 = base64.urlsafe_b64encode(self.request.data).decode().rstrip("=")
        signed_data = f"{protected_b64}.{payload_b64}".encode()

        # Decode the signature from base64url
        signature_bytes = self._b64url_decode(signature_b64)

        # Handle EC (ES256)
        alg = jwk.get("alg")
        if alg == "ES256":
            x_bytes = self._b64url_decode(jwk["x"])
            y_bytes = self._b64url_decode(jwk["y"])
            public_numbers = ec.EllipticCurvePublicNumbers(
                int.from_bytes(x_bytes, byteorder="big"),
                int.from_bytes(y_bytes, byteorder="big"),
                ec.SECP256R1(),
            )
            public_key = public_numbers.public_key(default_backend())

            # Always len(signature_bytes) == 64 for ES256
            r = int.from_bytes(signature_bytes[:32], "big")
            s = int.from_bytes(signature_bytes[32:], "big")
            signature_bytes = encode_dss_signature(r, s)

            try:
                public_key.verify(signature_bytes, signed_data, ec.ECDSA(SHA256()))
            except InvalidSignature as e:
                raise BancontactSignatureValidationError("ECDSA signature verification failed.") from e

        # Handle RSA (RS256)
        elif alg == "RS256":
            n = int.from_bytes(self._b64url_decode(jwk["n"]), byteorder="big")
            e = int.from_bytes(self._b64url_decode(jwk["e"]), byteorder="big")
            public_numbers = rsa.RSAPublicNumbers(e, n)
            public_key = public_numbers.public_key(default_backend())

            try:
                public_key.verify(signature_bytes, signed_data, padding.PKCS1v15(), SHA256())
            except InvalidSignature as e:
                raise BancontactSignatureValidationError("RSA signature verification failed.") from e

        # Unsupported key type
        else:
            raise BancontactSignatureValidationError(f"Unsupported JWK algorithm: {alg}")

    def _validate_critical_headers(self, protected):
        """Validate critical protected headers and extract the subject for later checks."""
        # -- crit
        crits = set(protected.get("crit", []))
        expected_crits = {
            const.ISS_KEY,
            const.IAT_KEY,
            const.JTI_KEY,
            const.PATH_KEY,
            const.SUB_KEY,
        }
        missing = expected_crits - crits
        unexpected = crits - expected_crits
        if missing or unexpected:
            raise BancontactSignatureValidationError(f"Invalid crit header: missing {missing}, unexpected {unexpected}")

        required = {
            const.ISS_KEY: protected.get(const.ISS_KEY),
            const.IAT_KEY: protected.get(const.IAT_KEY),
            const.JTI_KEY: protected.get(const.JTI_KEY),
            const.PATH_KEY: protected.get(const.PATH_KEY),
            const.SUB_KEY: protected.get(const.SUB_KEY),
        }
        missing = [key for key, value in required.items() if value is None]
        if missing:
            raise BancontactSignatureValidationError(f"Missing required protected header(s): {missing}")

        # -- iss
        issuer = required[const.ISS_KEY]
        if issuer != const.ISS_VALUE:
            raise BancontactSignatureValidationError(f"Invalid issuer: {issuer}")

        # -- iat
        iat_str = required[const.IAT_KEY]
        try:
            issued_at = datetime.strptime(iat_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            issued_at = issued_at.replace(tzinfo=UTC)
            now = datetime.now(UTC)
            delta = (now - issued_at).total_seconds()
            if abs(delta) > const.MAX_SKEW_SECONDS:
                raise BancontactSignatureValidationError(f"Invalid iat: outside allowed skew ({const.MAX_SKEW_SECONDS}s)")
        except (TypeError, ValueError) as e:
            raise BancontactSignatureValidationError(f"Invalid iat format: {iat_str}") from e

        # -- path
        expected_path = self.request.url.replace("http://", "https://")
        jws_path = protected.get(const.PATH_KEY).replace("http://", "https://")
        if jws_path != expected_path:
            raise BancontactSignatureValidationError(f"Path mismatch: {jws_path} != {expected_path}")

        # -- sub
        self.subject = protected.get(const.SUB_KEY)

    def _b64url_decode(self, data: str) -> bytes:
        try:
            data += "=" * 2
            return base64.urlsafe_b64decode(data)
        except (ValueError, TypeError, BinasciiError) as e:
            raise BancontactSignatureValidationError("Base64url decode error") from e

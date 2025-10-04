import base64
import binascii
import json
import logging
from datetime import datetime, timedelta, timezone
from json import JSONDecodeError

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.hashes import SHA256

from odoo import _, http, tools
from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.pos_payconiq import const

_logger = logging.getLogger(__name__)


class PayconiqController(http.Controller):
    @http.route(
        ["/webhook/payconiq"],
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def payconiq_webhook(self):
        """
        Handle the Payconiq webhook callback.

        This endpoint is triggered by Payconiq to notify about payment updates.
        It verifies the request signature, processes the payment data, and sends
        a synchronization message to the POS system.

        Returns:
            bool: True if the webhook is successfully processed, False otherwise.

        Raises:
            AccessDenied: If the Payconiq signature verification fails.
        """

        try:
            self.verify_payconiq_signature(request.httprequest)
        except AccessDenied as e:
            _logger.error("Payconiq signature verification failed: %s", e)
            return http.Response(status=403)

        data = request.get_json_data()
        pos_payment_payconiq = (
            self.env["pos.payment.payconiq"]
            .sudo()
            .search(
                [("payconiq_id", "=", data.get("paymentId", ""))],
                limit=1,
            )
        )

        if not pos_payment_payconiq:
            return http.Response(status=404)

        payload = {
            "status": data.get("status"),
            "uuid": pos_payment_payconiq.uuid,
        }

        pos_payment_payconiq.user_id._bus_send("pos_sync_payconiq", payload)
        return http.Response(status=200)

    # ========================================== #

    def verify_payconiq_signature(self, request):
        """
        Main entry point to verify the signature of a Payconiq callback request.

        Steps:
            1. Bypass signature check in test mode.
            2. Extract the protected header, signature, and key ID from the JWS.
            3. Retrieve the JWK (JSON Web Key) based on the key ID.
            4. Construct the public key object (EC or RSA) from the JWK.
            5. Verify the detached JWS signature using the request body.
            6. Validate all critical JOSE header fields required by Payconiq.

        Raises:
            AccessDenied: If the signature is invalid or critical header check fails.
        """

        if tools.config.get("test_enable"):
            return
        protected_b64, signature_b64, kid, protected = self._extract_jws_parts(request)
        jwk = self._get_jwk_by_kid(kid)
        public_key = self._build_public_key(jwk)
        self._verify_signature(
            public_key=public_key,
            protected_b64=protected_b64,
            body=request.data,
            signature_b64=signature_b64,
        )
        self._validate_critical_headers(protected, request.url)

    # ========================================== #

    def _verify_signature(
        self,
        public_key,
        protected_b64: str,
        body: bytes,
        signature_b64: str,
    ) -> None:
        """
        Verify the detached JWS signature using the reconstructed public key.
        Supports both ES256 (ECDSA) and RS256 (RSA) signatures.

        :param public_key: The EC public key object from the JWK.
        :param protected_b64: The base64url-encoded protected header string.
        :param body: The raw HTTP request body (as bytes).
        :param signature_b64: The base64url-encoded signature string.
        :raises AccessDenied: If the signature verification fails.
        """

        # Rebuild the signed input: base64url(protected header) + "." + base64url(payload)
        payload_b64 = base64.urlsafe_b64encode(body).decode().rstrip("=")
        signed_data = f"{protected_b64}.{payload_b64}".encode()

        # Decode the signature from base64url
        try:
            signature_bytes = self._b64url_decode(signature_b64)
        except (binascii.Error, Exception):
            msg = "Invalid base64 signature"
            raise AccessDenied(msg)

        # Handle EC (ES256)
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            try:
                public_key.verify(
                    signature_bytes,
                    signed_data,
                    ec.ECDSA(SHA256()),
                )
            except (InvalidSignature, Exception):
                msg = "ECDSA signature verification failed"
                raise AccessDenied(msg)

        # Handle RSA (RS256)
        elif isinstance(public_key, rsa.RSAPublicKey):
            try:
                public_key.verify(
                    signature_bytes,
                    signed_data,
                    padding.PKCS1v15(),
                    SHA256(),
                )
            except (InvalidSignature, Exception):
                msg = "RSA signature verification failed"
                raise AccessDenied(msg)

        # Unsupported key type
        else:
            msg = "Unsupported public key type"
            raise AccessDenied(msg)

    def _validate_critical_headers(self, protected: dict, request_url: str):
        """Validate Payconiq-specific critical headers in the JWS protected header."""
        crit_errors = []

        # Validate all crits are included
        crits = protected.get("crit", [])
        expected_crits = [
            const.ISS_KEY,
            const.IAT_KEY,
            const.JTI_KEY,
            const.PATH_KEY,
            const.SUB_KEY,
        ]
        missing_crits = [key for key in expected_crits if key not in crits]
        if missing_crits:
            crit_errors.append(f"Missing crits: {missing_crits}")

        # Validate issuer (iss)
        issuer = protected.get(const.ISS_KEY)
        if issuer != const.ISS_VALUE:
            crit_errors.append(f"Invalid issuer: {issuer}")

        # Validate issued-at time (iat) is recent
        iat_str = protected.get(const.IAT_KEY)
        try:
            issued_at = datetime.strptime(iat_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            issued_at = issued_at.replace(tzinfo=timezone.utc)
            delta = (datetime.now(timezone.utc) - issued_at).total_seconds()
            if delta > 500:
                crit_errors.append(f"Issued-at time too old: {iat_str}")
        except (ValueError, TypeError):
            crit_errors.append("Invalid or missing iat format")

        # Validate jti (unique ID)
        jti = protected.get(const.JTI_KEY)
        if not jti:
            crit_errors.append("Missing jti")

        # Validate path
        expected_path = request_url.replace("http://", "https://")
        jws_path = protected.get(const.PATH_KEY).replace(
            "http://",
            "https://",
        )
        if jws_path != expected_path:
            crit_errors.append(f"Path mismatch: {jws_path} != {expected_path}")

        # Validate subject matches the configured payment profile ID
        subject = protected.get(const.SUB_KEY)
        possible_subs = (
            self.env["pos.payment.method"]
            .sudo()
            .search([("use_payment_terminal", "=", "payconiq")])
            .mapped("payconiq_ppid")
        )
        if subject not in possible_subs:
            crit_errors.append(f"Invalid subject: {subject}")

        if crit_errors:
            raise AccessDenied(crit_errors)

    def _extract_jws_parts(self, request):
        """
        Extract the parts of a detached JWS signature from the HTTP request header.

        Returns:
            protected_b64: base64url-encoded protected header
            signature_b64: base64url-encoded signature
            kid: key ID used to retrieve the JWK
            protected: decoded JOSE header as dict
        """
        # Get the 'Signature' header
        signature = request.headers.get("Signature")
        if not signature:
            msg = "Missing Signature header"
            raise AccessDenied(msg)

        # The JWS is in the form: protected_b64..signature_b64 (note: payload is detached)
        try:
            protected_b64, _empty_playload_64, signature_b64 = signature.split(".")
        except (ValueError, Exception):
            msg = "Malformed Signature format"
            raise AccessDenied(msg)

        # Decode the protected header (JOSE header)
        try:
            protected_json = self._b64url_decode(protected_b64).decode("utf-8")
            protected = json.loads(protected_json)
            kid = protected["kid"]  # Get the Key ID used to fetch the JWK
        except (
            UnicodeDecodeError,
            JSONDecodeError,
            KeyError,
            binascii.Error,
            Exception,
        ) as e:
            raise AccessDenied(_("Unable to decode or parse protected header: %s", e))

        return protected_b64, signature_b64, kid, protected

    def _get_jwk_by_kid(self, kid: str):
        """Retrieve the JWK (JSON Web Key) by its Key ID (kid), retrying JWKS fetch if needed."""
        now = datetime.now(timezone.utc)
        cache = json.loads(
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("pos_payconiq.jwk_cache"),
        )
        cache_jwks = cache.get("jwks") if cache else None
        cache_timestamp = None
        if cache and cache.get("timestamp"):
            cache_timestamp = datetime.fromisoformat(cache["timestamp"])

        # Use cached JWKS if valid
        if (
            cache_jwks
            and cache_timestamp
            and (now - cache_timestamp) < timedelta(hours=const.JWKS_TTL)
        ):
            jwks = cache_jwks
        else:
            jwks = []

        # Extract the JWK with the matching kid
        def get_jwk_data():
            return next((key for key in jwks if key.get("kid") == kid), None)

        jwk_data = get_jwk_data()
        if jwk_data:
            return jwk_data

        # Fetch fresh JWKS from Payconiq if not found in cache
        response = requests.get(const.JWKS_URL, timeout=5)
        response.raise_for_status()
        jwks = response.json().get("keys", [])
        request.env["ir.config_parameter"].sudo().set_param(
            "pos_payconiq.jwk_cache",
            json.dumps(
                {
                    "timestamp": now.isoformat(),
                    "jwks": jwks,
                },
            ),
        )
        jwk_data = get_jwk_data()
        if jwk_data:
            return jwk_data

        # Still not found
        msg = "JWK with kid %s not found after JWKS refresh" % kid
        raise AccessDenied(msg)

    def _build_public_key(self, jwk: dict):
        """Build a public key object from the JWK data."""
        kty = jwk.get("kty")

        if kty == "EC":
            x_bytes = self._b64url_decode(jwk["x"])
            y_bytes = self._b64url_decode(jwk["y"])
            public_numbers = ec.EllipticCurvePublicNumbers(
                int.from_bytes(x_bytes, byteorder="big"),
                int.from_bytes(y_bytes, byteorder="big"),
                ec.SECP256R1(),
            )
            return public_numbers.public_key(default_backend())

        if kty == "RSA":
            n = int.from_bytes(self._b64url_decode(jwk["n"]), byteorder="big")
            e = int.from_bytes(self._b64url_decode(jwk["e"]), byteorder="big")
            public_numbers = rsa.RSAPublicNumbers(e, n)
            return public_numbers.public_key(default_backend())

        msg = f"Unsupported key type: {kty}"
        raise AccessDenied(msg)

    def _b64url_decode(self, data: str) -> bytes:
        """Decode a base64url-encoded string without padding."""
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

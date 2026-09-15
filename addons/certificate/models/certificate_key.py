import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding

from odoo import _, api, fields, models
from odoo.exceptions import UserError

STR_TO_HASH = {
    "sha1": hashes.SHA1(),  # noqa: S303 - kept for interoperability: signing/verification against legacy consumers still requiring SHA1 (e.g. government e-invoicing endpoints); this is a caller-selected option, not a hardcoded default
    "sha256": hashes.SHA256(),
}

STR_TO_CURVE = {
    "SECP256R1": ec.SECP256R1(),
}


def _get_formatted_bytes(data, formatting="encodebytes"):
    """Return wrapped Base64, compact Base64, or unchanged bytes for other modes."""
    if formatting == "encodebytes":
        return base64.encodebytes(data)
    elif formatting == "base64":
        return base64.b64encode(data)
    else:
        return data


def _int_to_bytes(value, byteorder="big"):
    return value.to_bytes((value.bit_length() + 7) // 8, byteorder=byteorder)


class CertificateKey(models.Model):
    _name = "certificate.key"
    _inherit = ["mixin.encryption"]
    _description = "Cryptographic Keys"

    _ENCRYPTED_FIELD_PAIRS = (
        ("content", "content_encrypted", True),
        ("password", "password_encrypted", False),
    )
    _ENCRYPTED_FALLBACK_FIELDS = {
        "content": "content_plain",
        "password": "password_plain",
    }

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(default="New key")
    active = fields.Boolean(
        default=True,
        name="Active",
        help="Set active to false to archive the key.",
    )
    content = fields.Binary(
        string="Key file",
        compute="_compute_content",
        inverse="_inverse_content",
        store=False,
        required=True,
    )
    content_encrypted = fields.Binary(
        string="Key file (encrypted)",
        attachment=False,
    )
    content_plain = fields.Binary(string="Key file (unencrypted)")
    password = fields.Char(
        string="Private key password",
        compute="_compute_password",
        inverse="_inverse_password",
        store=False,
    )
    password_encrypted = fields.Binary(
        string="Private key password (encrypted)",
        attachment=False,
    )
    password_plain = fields.Char(string="Private key password (unencrypted)")
    pem_key = fields.Binary(
        string="Key bytes in PEM format",
        compute="_compute_pem_key",
        search="_search_pem_key",
        store=False,
    )
    public = fields.Boolean(
        string="Public/Private key",
        compute="_compute_key_metadata",
        store=True,
    )
    loading_error = fields.Text(
        string="Loading error",
        compute="_compute_key_metadata",
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._stamp_encrypted_payload(vals_list)
        return records

    def write(self, vals):
        result = super().write(vals)
        self._stamp_encrypted_payload([vals] * len(self))
        return result

    @api.depends("content_encrypted", "content_plain")
    def _compute_content(self):
        self._compute_optional_encrypted_field(
            "content_encrypted",
            "content_plain",
            "content",
            binary=True,
        )

    @api.depends("password_encrypted", "password_plain")
    def _compute_password(self):
        self._compute_optional_encrypted_field(
            "password_encrypted",
            "password_plain",
            "password",
            binary=False,
        )

    def _inverse_content(self):
        self._inverse_optional_encrypted_field(
            "content",
            "content_encrypted",
            "content_plain",
            binary=True,
        )

    def _inverse_password(self):
        self._inverse_optional_encrypted_field(
            "password",
            "password_encrypted",
            "password_plain",
            binary=False,
        )

    @api.depends("content", "password")
    def _compute_pem_key(self):
        for key in self:
            pem_key, _public, _loading_error = self._get_pem_key_and_metadata(
                key.with_context(bin_size=False).content,
                key.password,
            )
            key.pem_key = pem_key

    @api.depends("content", "password")
    def _compute_key_metadata(self):
        for key in self:
            _pem_key, public, loading_error = self._get_pem_key_and_metadata(
                key.with_context(bin_size=False).content,
                key.password,
            )
            key.public = public
            key.loading_error = loading_error

    def _search_pem_key(self, operator, value):
        if operator not in ("in", "not in") or set(value) != {False}:
            return NotImplemented

        loaded = [
            "&",
            "|",
            ("content_encrypted", "!=", False),
            ("content_plain", "!=", False),
            ("loading_error", "=", ""),
        ]
        if operator == "not in":
            return loaded
        return ["!", *loaded]

    def _sign(self, message, hashing_algorithm="sha256", formatting="encodebytes"):
        self.check_singleton()

        if self.public:
            raise UserError(_("Make sure to use a private key to sign documents."))

        pem_key = self.with_context(bin_size=False).pem_key
        if self.loading_error:
            raise UserError(self.name + " - " + self.loading_error)

        return self._sign_with_key(
            message,
            pem_key,
            pwd=self.password,
            hashing_algorithm=hashing_algorithm,
            formatting=formatting,
        )

    def _execute_signature_verification(
        self, signed_message, signature, hashing_algorithm="sha256"
    ):
        """Verify with this public-key record, returning false for a bad signature.

        Invalid key configuration raises UserError; a signature mismatch does
        not. The signature argument contains raw signature bytes.

        :rtype: bool
        """
        self.check_singleton()

        if not self.public:
            raise UserError(
                _("Make sure to use a public key to verify the signature of documents.")
            )

        pem_key = self.with_context(bin_size=False).pem_key
        if self.loading_error:
            raise UserError(self.name + " - " + self.loading_error)

        return self._execute_signature_verification_with_key(
            signed_message,
            signature,
            pem_key,
            signature_algorithm=hashing_algorithm,
        )

    def _get_public_key_numbers_bytes(self, formatting="encodebytes"):
        self.check_singleton()

        return self._get_public_key_numbers_bytes_with_key(
            self._get_public_key_bytes(encoding="PEM"),
            formatting=formatting,
        )

    def _get_public_key_bytes(self, encoding="der", formatting="encodebytes"):
        self.check_singleton()

        if self.public:
            public_key = serialization.load_pem_public_key(
                base64.b64decode(self.with_context(bin_size=False).pem_key)
            )
        else:
            password = self.password
            if password and not isinstance(password, bytes):
                password = password.encode()
            public_key = serialization.load_pem_private_key(
                base64.b64decode(self.with_context(bin_size=False).pem_key),
                password or None,
            ).public_key()

        encoding = (
            serialization.Encoding.DER
            if encoding == "der"
            else serialization.Encoding.PEM
        )
        return _get_formatted_bytes(
            public_key.public_bytes(
                encoding=encoding,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
            formatting=formatting,
        )

    def _get_unencrypted_pem_key(self, formatting="base64"):
        self.check_singleton()

        if self.public:
            raise UserError(_("A private key is required."))
        if self.loading_error:
            raise UserError(self.name + " - " + self.loading_error)

        private_key = serialization.load_pem_private_key(
            base64.b64decode(self.with_context(bin_size=False).pem_key),
            self.password.encode() if self.password else None,
        )
        return _get_formatted_bytes(
            private_key.private_bytes(
                encoding=Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ),
            formatting=formatting,
        )

    @api.model
    def _get_pem_key_and_metadata(self, content, password=None):
        """Normalize encoded DER/PEM content and report its public/private kind.

        :returns: Base64-encoded PEM bytes, public-key flag and error text;
            missing or unloadable content returns None for the first two

        Preserve private-key password protection in the normalized PEM. An
        empty input has empty error text; rejected key formats have a message.
        """
        if not content:
            return None, None, ""

        pkey_content = base64.b64decode(content)
        pkey_password = password.encode("utf-8") if password else None

        pkey = None
        public = None
        for loader, is_public in (
            (
                lambda: serialization.load_der_private_key(pkey_content, pkey_password),
                False,
            ),
            (
                lambda: serialization.load_pem_private_key(pkey_content, pkey_password),
                False,
            ),
            (lambda: serialization.load_der_public_key(pkey_content), True),
            (lambda: serialization.load_pem_public_key(pkey_content), True),
        ):
            try:
                pkey = loader()
            except ValueError, TypeError:
                continue
            public = is_public
            break

        if not pkey:
            return (
                None,
                None,
                _(
                    "This key could not be loaded. Either its content or its password is erroneous."
                ),
            )

        if public:
            pem_key = base64.b64encode(
                pkey.public_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )
        else:
            encryption = (
                serialization.BestAvailableEncryption(pkey_password)
                if pkey_password
                else serialization.NoEncryption()
            )
            pem_key = base64.b64encode(
                pkey.private_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=encryption,
                )
            )

        return pem_key, public, ""

    def _decrypt(self, message, hashing_algorithm="sha256"):
        self.check_singleton()

        if not isinstance(message, bytes):
            message = message.encode("utf-8")

        if self.public:
            raise UserError(_("A private key is required to decrypt data."))
        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(  # pylint: disable=missing-gettext
                f"Unsupported hashing algorithm '{hashing_algorithm}'. Currently supported: sha1 and sha256."
            )

        password = self.password.encode("utf-8") if self.password else None
        try:
            private_key = serialization.load_pem_private_key(
                base64.b64decode(self.with_context(bin_size=False).pem_key), password
            )
        except (ValueError, TypeError) as exc:
            raise UserError(_("The private key could not be loaded.")) from exc
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise UserError(
                _(
                    "Unsupported asymmetric cryptography algorithm '%s'. Currently supported for decryption: RSA.",
                    type(private_key),
                )
            )

        return private_key.decrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=STR_TO_HASH[hashing_algorithm]),
                algorithm=STR_TO_HASH[hashing_algorithm],
                label=None,
            ),
        ).decode()

    @api.model
    def _sign_with_key(
        self,
        message,
        pem_key,
        pwd=None,
        hashing_algorithm="sha256",
        formatting="encodebytes",
    ):
        if not isinstance(message, bytes):
            message = message.encode("utf-8")
        if not isinstance(pem_key, bytes):
            pem_key = pem_key.encode("utf-8")
        if pwd and not isinstance(pwd, bytes):
            pwd = pwd.encode("utf-8")

        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(  # pylint: disable=missing-gettext
                f"Unsupported hashing algorithm '{hashing_algorithm}'. Currently supported: sha1 and sha256."
            )

        try:
            private_key = serialization.load_pem_private_key(
                base64.b64decode(pem_key), pwd or None
            )
        except ValueError as exc:
            raise UserError(_("The private key could not be loaded.")) from exc

        match private_key:
            case ec.EllipticCurvePrivateKey():
                signature = private_key.sign(
                    message, ec.ECDSA(STR_TO_HASH[hashing_algorithm])
                )
            case rsa.RSAPrivateKey():
                signature = private_key.sign(
                    message, padding.PKCS1v15(), STR_TO_HASH[hashing_algorithm]
                )
            case ed25519.Ed25519PrivateKey():
                signature = private_key.sign(message)
            case _:
                raise UserError(
                    _(
                        "Unsupported asymmetric cryptography algorithm '%s'. Currently supported for signature: ED25519, EC and RSA.",
                        type(private_key),
                    )
                )

        return _get_formatted_bytes(signature, formatting=formatting)

    @api.model
    def _execute_signature_verification_with_key(
        self, signed_message, signature, pem_key, signature_algorithm="sha256"
    ):
        """Verify raw signature bytes using a Base64-encoded public PEM key.

        Return false for a signature mismatch. Unusable keys or unsupported
        algorithms raise UserError. Ed25519 uses its own hash operation.

        :rtype: bool
        """

        def check_valid_signature_algorithm():
            if signature_algorithm not in STR_TO_HASH:
                raise UserError(  # pylint: disable=missing-gettext
                    f"Unsupported signature algorithm '{signature_algorithm}'. Currently supported: sha1 and sha256."
                )

        if not isinstance(signed_message, bytes):
            signed_message = signed_message.encode("utf-8")

        if not isinstance(pem_key, bytes):
            pem_key = pem_key.encode("utf-8")

        try:
            public_key = serialization.load_pem_public_key(base64.b64decode(pem_key))
        except ValueError as exc:
            raise UserError(_("The public key could not be loaded.")) from exc

        match public_key:
            case ec.EllipticCurvePublicKey():
                check_valid_signature_algorithm()
                try:
                    public_key.verify(
                        signature,
                        signed_message,
                        ec.ECDSA(STR_TO_HASH[signature_algorithm]),
                    )
                    return True
                except InvalidSignature:
                    return False
            case rsa.RSAPublicKey():
                check_valid_signature_algorithm()
                try:
                    public_key.verify(
                        signature,
                        signed_message,
                        padding.PKCS1v15(),
                        STR_TO_HASH[signature_algorithm],
                    )
                    return True
                except InvalidSignature:
                    return False
            case ed25519.Ed25519PublicKey():
                try:
                    public_key.verify(
                        signature,
                        signed_message,
                    )
                    return True
                except InvalidSignature:
                    return False
            case _:
                raise UserError(
                    _(
                        "Unsupported asymmetric cryptography algorithm '%s'. Currently supported for signature: EC and RSA.",
                        repr(public_key),
                    )
                )

    @api.model
    def _get_public_key_numbers_bytes_with_key(self, pem_key, formatting="encodebytes"):
        """Return RSA (exponent, modulus) or EC (x, y) as formatted byte strings.

        ``pem_key`` is Base64-encoded public PEM. Unsupported key types raise
        UserError; the selected formatting applies to each number separately.

        :rtype: tuple[bytes, bytes]
        """
        if not isinstance(pem_key, bytes):
            pem_key = pem_key.encode("utf-8")

        try:
            public_key = serialization.load_pem_public_key(base64.b64decode(pem_key))
        except ValueError as exc:
            raise UserError(_("The public key could not be loaded.")) from exc

        if isinstance(public_key, ec.EllipticCurvePublicKey):
            # EC keys have no modulus/exponent; this carries the curve
            # point coordinates (x, y) in the same two-value shape.
            first = public_key.public_numbers().x
            second = public_key.public_numbers().y
        elif isinstance(public_key, rsa.RSAPublicKey):
            first = public_key.public_numbers().e
            second = public_key.public_numbers().n
        else:
            raise UserError(
                _(
                    "Unsupported asymmetric cryptography algorithm '%s'. Currently supported: EC, RSA.",
                    type(public_key),
                )
            )

        return (
            _get_formatted_bytes(_int_to_bytes(first), formatting=formatting),
            _get_formatted_bytes(_int_to_bytes(second), formatting=formatting),
        )

    @api.model
    def _generate_ec_private_key(
        self, company, name="id_ec", curve="SECP256R1", password=None
    ):
        if curve not in STR_TO_CURVE:
            raise UserError(  # pylint: disable=missing-gettext
                f"Unsupported curve algorithm '{curve}'. Currently supported: SECP256R1."
            )

        private_key = ec.generate_private_key(STR_TO_CURVE[curve])

        if password and not isinstance(password, bytes):
            password = password.encode()

        return self.env["certificate.key"].create(
            {
                "name": name,
                "content": base64.b64encode(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.BestAvailableEncryption(
                            password
                        )
                        if password
                        else serialization.NoEncryption(),
                    )
                ),
                "company_id": company.id,
                "password": password,
            }
        )

    @api.model
    def _generate_rsa_private_key(
        self,
        company,
        name="id_rsa",
        public_exponent=65537,
        key_size=2048,
        password=None,
    ):
        if public_exponent not in [65537, 3]:
            raise UserError(
                _("The public exponent should be 65537 (or 3 for legacy purposes).")
            )
        if key_size < 512:
            raise UserError(_("The key size should be at least 512 bytes."))

        private_key = rsa.generate_private_key(
            public_exponent=public_exponent, key_size=key_size
        )

        if password and not isinstance(password, bytes):
            password = password.encode()

        encryption_algorithm = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )
        return self.env["certificate.key"].create(
            {
                "name": name,
                "content": base64.b64encode(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=encryption_algorithm,
                    )
                ),
                "company_id": company.id,
                "password": password,
            }
        )

    def _generate_ed25519_private_key(self, company, name="id_ed25519", password=None):
        private_key = ed25519.Ed25519PrivateKey.generate()

        if password and not isinstance(password, bytes):
            password = password.encode()

        return self.env["certificate.key"].create(
            {
                "name": name,
                "content": base64.b64encode(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.BestAvailableEncryption(
                            password
                        )
                        if password
                        else serialization.NoEncryption(),
                    )
                ),
                "company_id": company.id,
                "password": password,
            }
        )

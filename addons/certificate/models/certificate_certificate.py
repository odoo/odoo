import base64
from functools import lru_cache

from cryptography import x509
from cryptography.hazmat.primitives import constant_time, serialization
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .certificate_key import STR_TO_HASH, _get_formatted_bytes


@lru_cache(maxsize=128)
def _parse_x509_certificate(pem_bytes):
    """Parse PEM-encoded certificate bytes, memoized by content.

    ``_get_der_certificate_bytes``/``_get_fingerprint_bytes``/
    ``_get_signature_bytes``/``_get_public_key_bytes`` each call
    ``_get_parsed_certificate`` independently; a single signing flow that needs
    several of them re-parsed the same certificate from scratch every
    time. The cache key is the certificate's own bytes, so a changed
    ``pem_certificate`` never returns a stale parse.
    """
    return x509.load_pem_x509_certificate(pem_bytes)


class CertificateCertificate(models.Model):
    _name = "certificate.certificate"
    _inherit = ["mixin.encryption", "mixin.credential.holder"]
    _credential_holder_field = "certificate_credential_id"
    _credential_purpose = "certificate:secrets"
    _description = "Certificate"
    _order = "date_end DESC"
    _check_company_auto = True

    _ENCRYPTED_FIELD_PAIRS = (
        ("content", "content_encrypted", True),
        ("pkcs12_password", "pkcs12_password_encrypted", False),
    )
    _ENCRYPTED_FALLBACK_FIELDS = {
        "content": "content_plain",
        "pkcs12_password": "pkcs12_password_plain",
    }

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
        ondelete="cascade",
    )
    certificate_credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds the session and service secrets modules keep for this certificate.",
    )
    country_code = fields.Char(
        related="company_id.country_code",
        depends=["company_id"],
    )
    name = fields.Char()
    active = fields.Boolean(
        default=True,
        name="Active",
        help="Set active to false to archive the certificate",
    )
    content = fields.Binary(
        string="Certificate",
        compute="_compute_content",
        inverse="_inverse_content",
        store=False,
        readonly=False,
        required=True,
    )
    content_encrypted = fields.Binary(
        string="Certificate (encrypted)",
        attachment=False,
    )
    content_plain = fields.Binary(string="Certificate (unencrypted)")
    pkcs12_password = fields.Char(
        string="Certificate Password",
        compute="_compute_pkcs12_password",
        inverse="_inverse_pkcs12_password",
        store=False,
        help="Password to decrypt the PKS file.",
    )
    pkcs12_password_encrypted = fields.Binary(
        string="Certificate Password (encrypted)",
        attachment=False,
    )
    pkcs12_password_plain = fields.Char(string="Certificate Password (unencrypted)")
    private_key_id = fields.Many2one(
        comodel_name="certificate.key",
        compute="_compute_private_key_id",
        store=True,
        readonly=False,
        domain=[("public", "=", False)],
        check_company=True,
    )
    public_key_id = fields.Many2one(
        comodel_name="certificate.key",
        domain=[("public", "=", True)],
        check_company=True,
        help="""Used to set a public key in case the one self-contained in the certificate is erroneus.
                When a public key is set this way, it will be used instead of the one in the certificate.
             """,
    )
    scope = fields.Selection(
        selection=[
            ("general", "General"),
        ],
        string="Certificate scope",
        default="general",
        help="What this certificate may be used for. Every consumer selects on "
        "this field, so a certificate is inert until it is scoped "
        "deliberately -- 'General' is the safe default, not a fiscal role.",
    )
    content_format = fields.Selection(
        selection=[
            ("der", "DER"),
            ("pem", "PEM"),
            ("pkcs12", "PKCS12"),
        ],
        string="Original certificate format",
        compute="_compute_pem_certificate",
        store=True,
    )
    pem_certificate = fields.Binary(
        string="Certificate in PEM format",
        compute="_compute_pem_certificate",
        store=True,
    )
    subject_common_name = fields.Char(
        string="Subject Name",
        compute="_compute_pem_certificate",
        store=True,
    )
    serial_number = fields.Char(
        string="Serial number",
        compute="_compute_pem_certificate",
        store=True,
        help="The serial number to add to electronic documents",
    )
    date_start = fields.Datetime(
        string="Available date",
        compute="_compute_pem_certificate",
        store=True,
        help="The date on which the certificate starts to be valid",
    )
    date_end = fields.Datetime(
        string="Expiration date",
        compute="_compute_pem_certificate",
        store=True,
        help="The date on which the certificate expires",
    )
    loading_error = fields.Text(
        string="Loading error",
        compute="_compute_pem_certificate",
        store=True,
    )
    is_valid = fields.Boolean(
        string="Valid",
        compute="_compute_is_valid",
        search="_search_is_valid",
    )

    @api.constrains("pem_certificate", "private_key_id", "public_key_id")
    def _constrains_certificate_key_compatibility(self):
        for certificate in self:
            pem_certificate = certificate.with_context(bin_size=False).pem_certificate
            if pem_certificate:
                cert = x509.load_pem_x509_certificate(base64.b64decode(pem_certificate))
                cert_public_key_bytes = cert.public_key().public_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )

                if certificate.private_key_id:
                    if certificate.private_key_id.loading_error:
                        raise UserError(certificate.private_key_id.loading_error)
                    pkey_public_key_bytes = base64.b64decode(
                        certificate.private_key_id._get_public_key_bytes(encoding="pem")
                    )
                    if not constant_time.bytes_eq(
                        pkey_public_key_bytes, cert_public_key_bytes
                    ):
                        raise UserError(
                            _("The certificate and private key are not compatible.")
                        )

                if certificate.public_key_id:
                    if certificate.public_key_id.loading_error:
                        raise UserError(certificate.public_key_id.loading_error)
                    pkey_public_key_bytes = base64.b64decode(
                        certificate.public_key_id._get_public_key_bytes(encoding="pem")
                    )
                    if not constant_time.bytes_eq(
                        pkey_public_key_bytes, cert_public_key_bytes
                    ):
                        raise UserError(
                            _("The certificate and public key are not compatible.")
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

    @api.depends("pkcs12_password_encrypted", "pkcs12_password_plain")
    def _compute_pkcs12_password(self):
        self._compute_optional_encrypted_field(
            "pkcs12_password_encrypted",
            "pkcs12_password_plain",
            "pkcs12_password",
            binary=False,
        )

    @api.depends("pem_certificate")
    def _compute_private_key_id(self):
        for certificate in self:
            if not certificate.pem_certificate:
                certificate.private_key_id = None
                continue

            if certificate.private_key_id:
                continue

            if certificate.content_format == "pkcs12":
                content = certificate.with_context(bin_size=False).content
                pkcs12_password = (
                    certificate.pkcs12_password.encode("utf-8")
                    if certificate.pkcs12_password
                    else None
                )
                key, _cert, _additional_certs = pkcs12.load_key_and_certificates(
                    base64.b64decode(content), pkcs12_password
                )

                if key:
                    pem_key = base64.b64encode(
                        key.private_bytes(
                            encoding=Encoding.PEM,
                            format=serialization.PrivateFormat.PKCS8,
                            encryption_algorithm=serialization.NoEncryption(),
                        )
                    )
                    key_id = self._get_private_key_by_content(
                        pem_key, certificate.company_id
                    )
                    if not key_id:
                        key_id = self.env["certificate.key"].create(
                            {
                                "name": (
                                    certificate.subject_common_name
                                    or certificate.name
                                    or ""
                                )
                                + ".key",
                                "content": pem_key,
                                "company_id": certificate.company_id.id,
                            }
                        )
                    certificate.private_key_id = key_id

    @api.depends("content", "pkcs12_password")
    def _compute_pem_certificate(self):
        for certificate in self:
            content = certificate.with_context(bin_size=False).content

            if not content:
                certificate.pem_certificate = None
                certificate.subject_common_name = None
                certificate.content_format = None
                certificate.date_start = None
                certificate.date_end = None
                certificate.serial_number = None
                certificate.loading_error = ""

            else:
                content = base64.b64decode(content)
                cert = None

                try:
                    cert = x509.load_der_x509_certificate(content)
                    certificate.content_format = "der"
                except ValueError:
                    pass
                if not cert:
                    try:
                        pkcs12_password = (
                            certificate.pkcs12_password.encode("utf-8")
                            if certificate.pkcs12_password
                            else None
                        )
                        _key, cert, _additional_certs = (
                            pkcs12.load_key_and_certificates(content, pkcs12_password)
                        )
                        certificate.content_format = "pkcs12"
                    except ValueError:
                        pass
                if not cert:
                    try:
                        cert = x509.load_pem_x509_certificate(content)
                        certificate.content_format = "pem"
                    except ValueError:
                        pass

                if not cert:
                    certificate.pem_certificate = None
                    certificate.subject_common_name = None
                    certificate.content_format = None
                    certificate.date_start = None
                    certificate.date_end = None
                    certificate.serial_number = None
                    certificate.loading_error = _(
                        "This certificate could not be loaded. Either the content or the password is erroneous."
                    )
                    continue

                try:
                    common_name = cert.subject.get_attributes_for_oid(
                        x509.NameOID.COMMON_NAME
                    )
                    certificate.subject_common_name = (
                        common_name[0].value if common_name else ""
                    )
                except ValueError:
                    certificate.subject_common_name = None

                certificate.loading_error = ""

                certificate.pem_certificate = base64.b64encode(
                    cert.public_bytes(Encoding.PEM)
                )
                certificate.serial_number = cert.serial_number
                certificate.date_start = cert.not_valid_before_utc.replace(tzinfo=None)
                certificate.date_end = cert.not_valid_after_utc.replace(tzinfo=None)

    @api.depends("date_start", "date_end", "loading_error")
    def _compute_is_valid(self):
        now = fields.Datetime.now()
        for certificate in self:
            if (
                not certificate.date_start
                or not certificate.date_end
                or certificate.loading_error
            ):
                certificate.is_valid = False
            else:
                date_start = certificate.date_start
                date_end = certificate.date_end
                certificate.is_valid = date_start <= now <= date_end

    def _inverse_pkcs12_password(self):
        self._inverse_optional_encrypted_field(
            "pkcs12_password",
            "pkcs12_password_encrypted",
            "pkcs12_password_plain",
            binary=False,
        )

    def _inverse_content(self):
        self._inverse_optional_encrypted_field(
            "content",
            "content_encrypted",
            "content_plain",
            binary=True,
        )

    def _search_is_valid(self, operator, value):
        if operator != "in":
            return NotImplemented
        now = fields.Datetime.now()
        return [
            ("pem_certificate", "!=", False),
            ("date_start", "<=", now),
            ("date_end", ">=", now),
            ("loading_error", "=", ""),
        ]

    def _get_private_key_by_content(self, pem_key, company):
        """Return a matching private key in the company, including inactive keys.

        :return: ``certificate.key`` singleton, or an empty recordset
        """
        candidates = (
            self.env["certificate.key"]
            .with_context(active_test=False)
            .search(
                [("company_id", "=", company.id), ("public", "=", False)],
            )
        )
        return candidates.filtered(
            lambda key: key.with_context(bin_size=False).content == pem_key,
        )[:1]

    def _get_parsed_certificate(self):
        """Return the parsed X.509 certificate using the byte-keyed parse cache.

        :rtype: cryptography.x509.Certificate
        """
        self.check_singleton()
        return _parse_x509_certificate(
            base64.b64decode(self.with_context(bin_size=False).pem_certificate)
        )

    def _get_der_certificate_bytes(self, formatting="encodebytes"):
        self.check_singleton()
        cert = self._get_parsed_certificate()
        return _get_formatted_bytes(
            cert.public_bytes(serialization.Encoding.DER), formatting=formatting
        )

    def _get_fingerprint_bytes(
        self, hashing_algorithm="sha256", formatting="encodebytes"
    ):
        self.check_singleton()
        cert = self._get_parsed_certificate()
        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(  # pylint: disable=missing-gettext
                f"Unsupported hashing algorithm '{hashing_algorithm}'. Currently supported: sha1 and sha256."
            )
        return _get_formatted_bytes(
            cert.fingerprint(STR_TO_HASH[hashing_algorithm]), formatting=formatting
        )

    def _get_signature_bytes(self, formatting="encodebytes"):
        self.check_singleton()
        cert = self._get_parsed_certificate()
        return _get_formatted_bytes(cert.signature, formatting=formatting)

    def _get_public_key_numbers_bytes(self, formatting="encodebytes"):
        self.check_singleton()
        if self.public_key_id or self.private_key_id:
            return (
                self.public_key_id or self.private_key_id
            )._get_public_key_numbers_bytes(formatting=formatting)

        return self.env["certificate.key"]._get_public_key_numbers_bytes_with_key(
            self._get_public_key_bytes(encoding="pem"),
            formatting=formatting,
        )

    def _get_public_key_bytes(self, encoding="der", formatting="encodebytes"):
        self.check_singleton()
        if self.public_key_id or self.private_key_id:
            return (self.public_key_id or self.private_key_id)._get_public_key_bytes(
                encoding=encoding, formatting=formatting
            )

        try:
            public_key = self._get_parsed_certificate().public_key()
        except ValueError as e:
            raise UserError(
                _("The public key from the certificate could not be loaded.")
            ) from e

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

    def _sign(self, message, hashing_algorithm="sha256", formatting="encodebytes"):
        self.check_singleton()

        if not self.is_valid:
            raise UserError(
                self.loading_error
                or _("This certificate is not valid, its validity has expired.")
            )
        if not self.private_key_id:
            raise UserError(
                _(
                    "No private key linked to the certificate, it is required to sign documents."
                )
            )

        return self.private_key_id._sign(
            message, hashing_algorithm=hashing_algorithm, formatting=formatting
        )

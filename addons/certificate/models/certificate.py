import base64
from importlib import metadata
import re
from contextlib import suppress

from cryptography import x509
from cryptography.x509.oid import ExtensionOID, SignatureAlgorithmOID
from cryptography.x509.extensions import ExtensionNotFound
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import constant_time, serialization
from cryptography.hazmat.primitives.asymmetric import dsa, ec, ed448, ed25519, padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12, PublicFormat

from odoo import _, api, fields, models
from odoo.fields import Domain
from .key import STR_TO_HASH, _get_formatted_value
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import parse_version


class CertificateCertificate(models.Model):
    _name = 'certificate.certificate'
    _description = 'Certificate'
    _order = 'date_end DESC'
    _check_company_auto = True

    name = fields.Char(string='Name')
    content = fields.Binary(string='Certificate', readonly=False, required=True)
    pkcs12_password = fields.Char(string='Certificate Password', help='Password to decrypt the PKS file.')
    private_key_id = fields.Many2one(
        string='Private Key',
        comodel_name='certificate.key',
        check_company=True,
        domain=[('public', '=', False)],
        compute='_compute_private_key',
        store=True,
        readonly=False,
    )
    public_key_id = fields.Many2one(
        string='Public Key',
        comodel_name='certificate.key',
        check_company=True,
        domain=[('public', '=', True)],
        help="""Used to set a public key in case the one self-contained in the certificate is erroneus.
                When a public key is set this way, it will be used instead of the one in the certificate.
             """,
    )
    scope = fields.Selection(
        string="Certificate scope",
        selection=[
            ('general', 'General'),
        ],
    )
    content_format = fields.Selection(
        selection=[
            ('der', 'DER'),
            ('pem', 'PEM'),
            ('pkcs12', 'PKCS12'),
        ],
        string='Original certificate format',
        compute='_compute_pem_certificate',
        store=True,
    )
    pem_certificate = fields.Binary(
        string='Certificate in PEM format',
        compute='_compute_pem_certificate',
        store=True,
    )
    subject_common_name = fields.Char(
        string='Subject Name',
        compute='_compute_pem_certificate',
        store=True,
    )
    serial_number = fields.Char(
        string='Serial number',
        help='The serial number to add to electronic documents',
        compute='_compute_pem_certificate',
        store=True,
    )
    date_start = fields.Datetime(
        string='Available date',
        help='The date on which the certificate starts to be valid',
        compute='_compute_pem_certificate',
        store=True,
    )
    date_end = fields.Datetime(
        string='Expiration date',
        help='The date on which the certificate expires',
        compute='_compute_pem_certificate',
        store=True,
    )
    loading_error = fields.Text(string='Loading error', compute='_compute_pem_certificate', store=True)
    is_valid = fields.Boolean(string='Valid', compute='_compute_is_valid', search='_search_is_valid')
    active = fields.Boolean(name='Active', help='Set active to false to archive the certificate', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    country_code = fields.Char(related='company_id.country_code', depends=['company_id'])
    issuer_cert_id = fields.Many2one(
        comodel_name='certificate.certificate',
        string='Issuer Certificate',
        compute='_compute_issuer_cert_id',
        check_company=True,
    )

    @api.depends('pem_certificate', 'subject_common_name', 'company_id')
    def _compute_issuer_cert_id(self):
        def load_certificate(certificate):
            with suppress(ValueError, TypeError):
                return x509.load_pem_x509_certificate(base64.b64decode(
                    certificate.with_context(bin_size=False).pem_certificate
                ))
            return False

        # By default, put no issuer
        self.issuer_cert_id = False

        # Build cert_data only for certificates we can load
        cert_data = {
            certificate: {
                'loaded': loaded_certificate,
                'issuer_cn': issuer_cn,
            }
            for certificate in self.filtered('pem_certificate')
            if (loaded_certificate := load_certificate(certificate))
            if (issuer_cn := self._get_common_name(loaded_certificate.issuer))
        }

        if cert_data:
            valid_certs = self.filtered(lambda c: c in cert_data)
            possible_parents = self.with_context(active_test=False).env['certificate.certificate'].search([
                *self.env['certificate.certificate']._check_company_domain(valid_certs.mapped('company_id')),
                ('subject_common_name', 'in', list({d['issuer_cn'] for d in cert_data.values()})),
                ('pem_certificate', '!=', False),
            ])

            for cert, data in cert_data.items():
                candidates = possible_parents.filtered_domain([
                    *self.env['certificate.certificate']._check_company_domain(cert.company_id),
                    ('subject_common_name', '=', data['issuer_cn']),
                    # Exclude the certificate itself so a self-signed cert (subject == issuer)
                    # is not matched as its own issuer
                    ('id', '!=', cert.id),
                # Prefer the candidate with the furthest expiration date (most recent renewal)
                ]).sorted(key=lambda p: p.date_end or fields.Datetime.now(), reverse=True)

                # A candidate whose key cryptographically signed this certificate.
                issuer = candidates.filtered(
                    lambda candidate: (x509_candidate := load_certificate(candidate))
                    and self._is_issued_by(data['loaded'], x509_candidate)
                )[:1]

                # No mathematical proof: fall back to a
                # candidate whose SKI matches the expected issuer key identifier (AKI).
                expected_ski = self._get_authority_key_identifier(data['loaded'])
                if not issuer and expected_ski:
                    issuer = candidates.filtered(
                        lambda candidate: (x509_candidate := load_certificate(candidate))
                        and self._get_subject_key_identifier(x509_candidate) == expected_ski
                    )[:1]

                cert.issuer_cert_id = issuer.id

    @api.depends('pem_certificate')
    def _compute_private_key(self):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'certificate.key'),
            ('res_field', '=', 'content'),
            ('res_id', 'in', self.ids)
        ])
        content_to_key_id = {(att.datas, att.company_id.id): att.res_id for att in attachments}

        for certificate in self:
            if not certificate.pem_certificate:
                certificate.private_key_id = None
                continue

            content = certificate.with_context(bin_size=False).content
            key_password = certificate.pkcs12_password.encode('utf-8') if certificate.pkcs12_password else None
            key = None

            # Create the private key if using PKCS12 or PEM files and no private key is set
            if certificate.content_format == 'pkcs12':
                key, _cert, _additional_certs = pkcs12.load_key_and_certificates(base64.b64decode(content), key_password)
            elif certificate.content_format == 'pem':
                with suppress(ValueError, TypeError, UnsupportedAlgorithm):
                    key = serialization.load_pem_private_key(base64.b64decode(content), password=key_password)

            if key:
                pem_key = base64.b64encode(key.private_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                key_id = content_to_key_id.get((pem_key, certificate.company_id.id))
                if not key_id:
                    key_id = self.env['certificate.key'].create({
                        'name': (certificate.subject_common_name or certificate.name or "") + ".key",
                        'content': pem_key,
                        'company_id': certificate.company_id.id,
                    })
                certificate.private_key_id = key_id

    @api.depends('content', 'pkcs12_password')
    def _compute_pem_certificate(self):
        def reset_certificate(record):
            record.pem_certificate = False
            record.subject_common_name = False
            record.content_format = False
            record.date_start = False
            record.date_end = False
            record.serial_number = False
            record.loading_error = False

        for certificate in self:
            content = certificate.with_context(bin_size=False).content

            if not content:
                reset_certificate(certificate)
                continue

            pkcs12_password = certificate.pkcs12_password.encode('utf-8') if certificate.pkcs12_password else None
            leaf_pem, _additional_pems, certificate.content_format = self._parse_certificate_content(content, pkcs12_password)

            if not leaf_pem:
                reset_certificate(certificate)
                if certificate.pkcs12_password:
                    certificate.loading_error = _(
                        "This certificate could not be loaded. Either the content or the password is erroneous."
                    )
                continue

            cert = x509.load_pem_x509_certificate(leaf_pem)
            certificate.loading_error = ""

            # Extract certificate data
            certificate.pem_certificate = base64.b64encode(leaf_pem)
            certificate.serial_number = cert.serial_number
            certificate.subject_common_name = self._get_common_name(cert.subject) or cert.serial_number
            if parse_version(metadata.version('cryptography')) < parse_version('42.0.0'):
                certificate.date_start = cert.not_valid_before
                certificate.date_end = cert.not_valid_after
            else:
                certificate.date_start = cert.not_valid_before_utc.replace(tzinfo=None)
                certificate.date_end = cert.not_valid_after_utc.replace(tzinfo=None)

    @api.depends('date_start', 'date_end', 'loading_error')
    def _compute_is_valid(self):
        # Certificate dates and Odoo datetimes are UTC timezoned
        # https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate.not_valid_after
        now = fields.Datetime.now()
        for certificate in self:
            if not certificate.date_start or not certificate.date_end or certificate.loading_error:
                certificate.is_valid = False
            else:
                date_start = certificate.date_start
                date_end = certificate.date_end
                certificate.is_valid = date_start <= now <= date_end

    def _search_is_valid(self, operator, value):
        if operator != 'in':
            return NotImplemented
        now = fields.Datetime.now()
        return [
            ('pem_certificate', '!=', False),
            ('date_start', '<=', now),
            ('date_end', '>=', now),
            ('loading_error', '=', '')
        ]

    @api.constrains('pem_certificate', 'private_key_id', 'public_key_id')
    def _constrains_certificate_key_compatibility(self):
        for certificate in self:
            pem_certificate = certificate.with_context(bin_size=False).pem_certificate
            if pem_certificate:
                cert = x509.load_pem_x509_certificate(base64.b64decode(pem_certificate))
                cert_public_key_bytes = cert.public_key().public_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )

                if certificate.private_key_id:
                    if certificate.private_key_id.loading_error:
                        raise ValidationError(certificate.private_key_id.loading_error)
                    pkey_public_key_bytes = base64.b64decode(
                        certificate.private_key_id._get_public_key_bytes(encoding='pem')
                    )
                    if not constant_time.bytes_eq(pkey_public_key_bytes, cert_public_key_bytes):
                        raise ValidationError(_("The certificate and private key are not compatible."))

                if certificate.public_key_id:
                    if certificate.public_key_id.loading_error:
                        raise ValidationError(certificate.public_key_id.loading_error)
                    pkey_public_key_bytes = base64.b64decode(
                        certificate.public_key_id._get_public_key_bytes(encoding='pem')
                    )
                    if not constant_time.bytes_eq(pkey_public_key_bytes, cert_public_key_bytes):
                        raise ValidationError(_("The certificate and public key are not compatible."))

    @api.constrains('content', 'pem_certificate')
    def _constrains_certificate_loaded(self):
        for certificate in self.filtered(lambda c: c.content and not c.pem_certificate):
            raise ValidationError(
                certificate.loading_error
                or _("This certificate could not be loaded. Please provide the certificate password.")
            )

    # -------------------------------------------------------
    # Content Extraction Logic
    # -------------------------------------------------------
    @api.model
    def _get_subject_key_identifier(self, x509_cert):
        """ Helper to safely extract the Subject Key Identifier (SKI) """
        with suppress(ExtensionNotFound):
            return x509_cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_KEY_IDENTIFIER).value.digest
        return None

    @api.model
    def _get_authority_key_identifier(self, x509_cert):
        """ Helper to safely extract the Authority Key Identifier (AKI) """
        with suppress(ExtensionNotFound):
            return x509_cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_KEY_IDENTIFIER).value.key_identifier
        return None

    @api.model
    def _get_common_name(self, x509_name):
        """ Helper to safely extract the common name of a certificate. Pass cert.subject or cert.issuer directly here """
        with suppress(ValueError, IndexError):
            return x509_name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        return None

    @api.model
    def _is_issued_by(self, x509_certificate, x509_issuer_certificate):
        """ Cryptographically check that ``certificate`` was directly issued by
        ``issuer_certificate``: the issuer distinguished name must match and the
        signature must verify against the issuer's public key.

        :return: ``True`` if the issuance is cryptographically proven, ``False`` if it
            is disproven, and ``None`` if it could not be checked (unsupported scheme or
            parameters).
        :rtype: bool | None
        """
        if x509_certificate.issuer != x509_issuer_certificate.subject:
            return False

        public_key = x509_issuer_certificate.public_key()
        signature = x509_certificate.signature
        signed_bytes = x509_certificate.tbs_certificate_bytes
        hash_alg = x509_certificate.signature_hash_algorithm

        # Each branch builds the argument tuples to try with ``public_key.verify`` and the
        # result when none succeed (False = disproven, None = could not be checked).
        match public_key:
            case ed25519.Ed25519PublicKey() | ed448.Ed448PublicKey():
                attempts, on_failure = [(signature, signed_bytes)], False
            case _ if hash_alg is None:
                # A hash-less signature (Ed25519/Ed448) cannot have been produced by this key.
                attempts, on_failure = [], False
            case ec.EllipticCurvePublicKey():
                attempts, on_failure = [(signature, signed_bytes, ec.ECDSA(hash_alg))], False
            case dsa.DSAPublicKey():
                attempts, on_failure = [(signature, signed_bytes, hash_alg)], False
            case rsa.RSAPublicKey() if x509_certificate.signature_algorithm_oid != SignatureAlgorithmOID.RSASSA_PSS:
                attempts, on_failure = [(signature, signed_bytes, padding.PKCS1v15(), hash_alg)], False
            case rsa.RSAPublicKey():
                # RSA-PSS: we assume MGF1 with the signature hash and try the two conventional
                # salt lengths (DIGEST_LENGTH then MAX_LENGTH). A non-standard MGF hash or an
                # arbitrary salt length is not covered, so failing both is inconclusive (None).
                attempts = [
                    (signature, signed_bytes, padding.PSS(mgf=padding.MGF1(hash_alg), salt_length=salt_length), hash_alg)
                    for salt_length in (hash_alg.digest_size, padding.PSS.MAX_LENGTH)
                ]
                on_failure = None
            case _:
                attempts, on_failure = [], None  # unsupported key type

        for verify_args in attempts:
            with suppress(InvalidSignature, TypeError, ValueError):
                public_key.verify(*verify_args)
                return True
        return on_failure

    @api.model
    def _parse_pem_certificate_bundle(self, decoded_content, password=None):
        """
        Parses a PEM-encoded bundle to extract individual certificate blocks and
        orders them based on the provided private key.

        The function attempts to load a private key from the bundle. If successful,
        it compares public keys to identify the main target certificate. The first
        certificate in the returned list is guaranteed to be the leaf certificate,
        followed by the rest of the CA chain. If no private key is found, it returns
        the certificates in their original order.
        """

        def subject(obj):
            return obj.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

        cert_blocks = re.findall(rb'(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)', decoded_content, flags=re.DOTALL)

        try:
            # Catch errors because the bundle might only contain public certificates
            # (like a CA bundle) and lack a private key, or the password could be missing/incorrect.
            private_key = serialization.load_pem_private_key(decoded_content, password=password)
        except (ValueError, TypeError, UnsupportedAlgorithm):
            return cert_blocks

        target_pub_bytes = subject(private_key)
        chain_blocks = []
        for block in cert_blocks:
            curr_pub_bytes = subject(x509.load_pem_x509_certificate(block))
            if curr_pub_bytes == target_pub_bytes:
                chain_blocks.insert(0, block)
            else:
                chain_blocks.append(block)

        return chain_blocks

    @api.model
    def _parse_certificate_content(self, content, password=None):
        content = base64.b64decode(content)

        def pem(x):
            return x.public_bytes(Encoding.PEM) if x else None

        # Try to load the certificate in different format starting with DER then PKCS12 and finally PEM.
        with suppress(ValueError):
            return pem(x509.load_der_x509_certificate(content)), [], 'der'

        with suppress(ValueError):
            _key, leaf_cert, additional_certs = pkcs12.load_key_and_certificates(content, password)
            return pem(leaf_cert), [pem(x) for x in additional_certs], 'pkcs12'

        with suppress(ValueError):
            leaf, *additional = self._parse_pem_certificate_bundle(content, password)
            return leaf, additional, 'pem'

        return None, [], None

    @api.model
    def _extract_and_filter_chain(self, content_bytes, password=None):
        """ Parses a bundle and returns only the certificates forming the leaf's chain """
        leaf_pem, additional_pems, _ = self._parse_certificate_content(content_bytes, password)
        if not leaf_pem:
            return [None]

        ski_cert_map = {}
        for pem in additional_pems:
            cert = x509.load_pem_x509_certificate(pem)
            if ski := self._get_subject_key_identifier(cert):
                ski_cert_map[ski] = cert

        leaf_cert = x509.load_pem_x509_certificate(leaf_pem)
        certs_chain = [leaf_cert]
        current_cert = leaf_cert

        # Traverse upward: Current AKI -> Parent SKI
        while (
            (aki := self._get_authority_key_identifier(current_cert))
            and (parent_cert := ski_cert_map.get(aki))
            and parent_cert not in certs_chain  # Prevents infinite loops (e.g., self-signed roots)
        ):
            certs_chain.append(parent_cert)
            current_cert = parent_cert

        return [c.public_bytes(Encoding.PEM) for c in certs_chain]

    # -------------------------------------------------------
    # ORM Overrides for Auto-CA Creation
    # -------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list + [
            ca_vals
            for vals in vals_list
            for ca_vals in self._parse_chain_missing_ca_vals({
                **vals,
                'company_id': vals.get('company_id') or self.env.company.id
            })
        ])[:len(vals_list)]

    def write(self, vals):
        res = super().write(vals)

        if 'content' in vals or 'pkcs12_password' in vals:
            if ca_vals_list := [
                ca_vals
                for record in self
                for ca_vals in self._parse_chain_missing_ca_vals({
                    'content': record.with_context(bin_size=False).content,
                    'pkcs12_password': record.pkcs12_password,
                    'company_id': record.company_id.id,
                    **vals,
                })
                if record.content and not record.loading_error
            ]:
                self.env['certificate.certificate'].create(ca_vals_list)

        return res

    @api.model
    def _parse_chain_missing_ca_vals(self, vals):
        """
        Parses the certificate content to extract its CA chain and identifies which
        Certificate Authorities are missing from the database.

        :return: A list of field dictionaries ready to be passed to `create()` for the missing CAs.
        """

        def get_cert_data(pem):
            ca_cert = x509.load_pem_x509_certificate(pem)
            serial_number = str(ca_cert.serial_number)
            subject = self._get_common_name(ca_cert.subject) or serial_number
            return {
                'name': f"{subject} (CA)",
                'company_id': company_id,
                'serial_number': serial_number,
                'subject_common_name': subject,
                'content': base64.b64encode(pem),
                'active': False,
            }

        company_id = vals.get('company_id')
        password = vals.get('pkcs12_password', '').encode('utf-8') if vals.get('pkcs12_password') else None
        content = vals.get('content', b'')

        _leaf_pem, *ca_pems = self._extract_and_filter_chain(content, password)
        if not ca_pems:
            return []

        ca_data_list = [get_cert_data(pem) for pem in ca_pems]

        # Search for existing certificates to avoid duplicates
        domain = [
            *self.env['certificate.certificate']._check_company_domain(company_id),
            ('serial_number', 'in', [d['serial_number'] for d in ca_data_list]),
        ]
        existing_records = self.with_context(active_test=False).search_read(
            domain, ['serial_number', 'subject_common_name']
        )
        existing_certs_key = {(r['serial_number'], r['subject_common_name']) for r in existing_records}

        ca_create_vals = []
        for ca_data in ca_data_list:
            key = (ca_data['serial_number'], ca_data['subject_common_name'])
            if key not in existing_certs_key:
                ca_create_vals.append(ca_data)
                # Add to existing_certs_key to handle duplicates within the same chain
                existing_certs_key.add(key)

        return ca_create_vals

    # -------------------------------------------------------
    #                   Business Methods                    #
    # -------------------------------------------------------

    def _get_der_certificate_bytes(self, formatting='encodebytes'):
        ''' Get the DER bytes of the certificate.

        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted DER bytes of the certificate
        :rtype: bytes
        '''
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.with_context(bin_size=False).pem_certificate))
        return _get_formatted_value(cert.public_bytes(serialization.Encoding.DER), formatting=formatting)

    def _get_fingerprint_bytes(self, hashing_algorithm='sha256', formatting='encodebytes'):
        ''' Get the fingerprint bytes of the certificate.

        :param optional,default='sha256' hashing_algorithm: The digest algorithm to use. Currently, only 'sha1' and 'sha256' are available.
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted fingerprint bytes of the certificate
        :rtype: bytes
        '''
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.with_context(bin_size=False).pem_certificate))
        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(f"Unsupported hashing algorithm '{hashing_algorithm}'. Currently supported: sha1 and sha256.")  # pylint: disable=missing-gettext
        return _get_formatted_value(cert.fingerprint(STR_TO_HASH[hashing_algorithm]), formatting=formatting)

    def _get_signature_bytes(self, formatting='encodebytes'):
        ''' Get the signature bytes of the certificate.

        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted signature bytes of the certificate
        :rtype: bytes
        '''
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.with_context(bin_size=False).pem_certificate))
        return _get_formatted_value(cert.signature, formatting=formatting)

    def _get_public_key_numbers_bytes(self, formatting='encodebytes'):
        ''' Get the certificate public key's public numbers bytes.

        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: A tuple containing the formatted public number bytes of the certificate's public key

        :rtype: tuple(bytes,bytes)
        '''
        self.ensure_one()
        if self.public_key_id or self.private_key_id:
            return (self.public_key_id or self.private_key_id)._get_public_key_numbers_bytes(formatting=formatting)

        # When no keys are set to the certificate, use the self-contained public key from the content
        return self.env['certificate.key']._numbers_public_key_bytes_with_key(
            self._get_public_key_bytes(encoding='pem'),
            formatting=formatting,
        )

    def _get_public_key_bytes(self, encoding='der', formatting='encodebytes'):
        ''' Get the certificate's public key bytes.

        :param optional,default='der' encoding: The formatting of the returned bytes
            - 'der' returns DER public key bytes
            - other returns PEM public key bytes
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted certificate public key bytes in the corresponding format
        :rtype: bytes
        '''
        self.ensure_one()
        if self.public_key_id or self.private_key_id:
            return (self.public_key_id or self.private_key_id)._get_public_key_bytes(encoding=encoding, formatting=formatting)

        # When no keys are set to the certificate, use the self-contained public key from the content
        try:
            cert = x509.load_pem_x509_certificate(base64.b64decode(self.with_context(bin_size=False).pem_certificate))
            public_key = cert.public_key()
        except ValueError:
            raise UserError(_("The public key from the certificate could not be loaded."))

        encoding = serialization.Encoding.DER if encoding == 'der' else serialization.Encoding.PEM
        return _get_formatted_value(
            public_key.public_bytes(
                encoding=encoding,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            formatting=formatting,
        )

    def _sign(self, message, hashing_algorithm='sha256', formatting='encodebytes'):
        ''' Compute and return the message's signature.

        :param str|bytes message: The message to sign
        :param optional,default='sha256' hashing_algorithm: The digest algorithm to use. Currently, only 'sha1' and 'sha256' are available.
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted signature bytes of the message
        :rtype: bytes
        '''
        self.ensure_one()

        if not self.is_valid:
            raise UserError(self.loading_error or _("This certificate is not valid, its validity has expired."))
        if not self.private_key_id:
            raise UserError(_("No private key linked to the certificate, it is required to sign documents."))

        return self.private_key_id._sign(message, hashing_algorithm=hashing_algorithm, formatting=formatting)

    def _get_certificate_chain(self):
        """
        Retrieves the full certificate chain as a recordset, starting from the current
        certificate and walking up the issuer_cert_id links.

        :return: A recordset of certificate.certificate objects ordered from Leaf to Root.
        """
        self.ensure_one()

        chain = self
        while (
            (current_cert := chain[-1].issuer_cert_id)
            and current_cert not in chain
        ):
            chain += current_cert

        return chain

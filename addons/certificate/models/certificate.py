import base64
from importlib import metadata

from cryptography import x509
from cryptography.hazmat.primitives import constant_time, serialization
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12

from odoo import _, api, fields, models
from .key import STR_TO_HASH, _get_formatted_value
from odoo.exceptions import UserError
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

            if certificate.private_key_id:
                continue

            # Create the private key in case of PKCS12 File and no private key is set
            if certificate.content_format == 'pkcs12':
                content = certificate.with_context(bin_size=False).content
                pkcs12_password = certificate.pkcs12_password.encode('utf-8') if certificate.pkcs12_password else None
                key, _cert, _additional_certs = pkcs12.load_key_and_certificates(base64.b64decode(content), pkcs12_password)

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

                # Try to load the certificate in different format starting with DER then PKCS12 and
                # finally PEM. If none succeeded, we report an error.
                try:
                    cert = x509.load_der_x509_certificate(content)
                    certificate.content_format = 'der'
                except ValueError:
                    pass
                if not cert:
                    try:
                        pkcs12_password = certificate.pkcs12_password.encode('utf-8') if certificate.pkcs12_password else None
                        _key, cert, _additional_certs = pkcs12.load_key_and_certificates(content, pkcs12_password)
                        certificate.content_format = 'pkcs12'
                    except ValueError:
                        pass
                if not cert:
                    try:
                        cert = x509.load_pem_x509_certificate(content)
                        certificate.content_format = 'pem'
                    except ValueError:
                        pass

                if not cert:
                    certificate.pem_certificate = None
                    certificate.subject_common_name = None
                    certificate.content_format = None
                    certificate.date_start = None
                    certificate.date_end = None
                    certificate.serial_number = None
                    certificate.loading_error = _("This certificate could not be loaded. Either the content or the password is erroneous.")
                    continue

                try:
                    common_name = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
                    certificate.subject_common_name = common_name[0].value if common_name else ""
                except ValueError:
                    certificate.subject_common_name = None

                certificate.loading_error = ""

                # Extract certificate data
                certificate.pem_certificate = base64.b64encode(cert.public_bytes(Encoding.PEM))
                certificate.serial_number = cert.serial_number
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
                        raise UserError(certificate.private_key_id.loading_error)
                    pkey_public_key_bytes = base64.b64decode(
                        certificate.private_key_id._get_public_key_bytes(encoding='pem')
                    )
                    if not constant_time.bytes_eq(pkey_public_key_bytes, cert_public_key_bytes):
                        raise UserError(_("The certificate and private key are not compatible."))

                if certificate.public_key_id:
                    if certificate.public_key_id.loading_error:
                        raise UserError(certificate.public_key_id.loading_error)
                    pkey_public_key_bytes = base64.b64decode(
                        certificate.public_key_id._get_public_key_bytes(encoding='pem')
                    )
                    if not constant_time.bytes_eq(pkey_public_key_bytes, cert_public_key_bytes):
                        raise UserError(_("The certificate and public key are not compatible."))

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

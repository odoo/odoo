import base64
import datetime

from cryptography import x509
from cryptography.hazmat.primitives import constant_time, serialization
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12

from odoo import _, api, fields, models
from .key import STR_TO_HASH
from odoo.exceptions import UserError


class Certificate(models.Model):
    _name = 'certificate.certificate'
    _description = 'Certificate'
    _order = 'date_end DESC'
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string='Name', default="New certificate")
    content = fields.Binary(string='Certificate', required=True)
    pkcs12_password = fields.Char(string='Certificate Password', help='Password to decrypt the PKS file.')
    private_key = fields.Many2one(
        string='Private Key',
        comodel_name='certificate.key',
        check_company=True,
        domain=[('public', '=', False)]
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
        store=True,
        compute='_compute_pem_certificate',
    )
    pem_certificate = fields.Binary(
        string='Certificate in PEM format',
        attachment=False,
        store=True,
        compute='_compute_pem_certificate'
    )
    serial_number = fields.Char(
        string='Serial number',
        help='The serial number to add to electronic documents',
        compute='_compute_pem_certificate',
        store=True,
    )
    date_start = fields.Datetime(
        string='Available date',
        help='The date on which the certificate starts to be valid (UTC)',
        compute='_compute_pem_certificate',
        store=True,
    )
    date_end = fields.Datetime(
        string='Expiration date',
        help='The date on which the certificate expires (UTC)',
        compute='_compute_pem_certificate',
        store=True,
    )
    is_valid = fields.Boolean(string='Valid', compute='_compute_is_valid', search='_search_is_valid')
    active = fields.Boolean(name='Active', help='Set active to false to archive the certificate.', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )
    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id'])

    @api.constrains('pem_certificate', 'private_key')
    def _constrains_certificate_key_compatibility(self):
        for certificate in self:
            if certificate.pem_certificate and certificate.private_key:
                cert = x509.load_pem_x509_certificate(base64.b64decode(certificate.pem_certificate))
                cert_public_key_bytes = cert.public_key().public_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                pkey = serialization.load_pem_private_key(base64.b64decode(certificate.private_key.pem_key), None)
                pkey_public_key_bytes = pkey.public_key().public_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                if not constant_time.bytes_eq(pkey_public_key_bytes, cert_public_key_bytes):
                    raise UserError(_("The certificate and private key are not compatible."))

    @api.depends('content', 'pkcs12_password')
    def _compute_pem_certificate(self):
        cert_with_content = self.filtered('content')

        for certificate in self - cert_with_content:
            certificate.pem_certificate = None
            certificate.date_start = None
            certificate.date_end = None
            certificate.serial_number = None
            certificate.private_key = None
            certificate.scope = certificate.scope or certificate.env.context.get('scope', 'general')

        for certificate in cert_with_content:
            content = base64.b64decode(certificate.content)
            cert = key = None

            certificate.scope = certificate.scope or certificate.env.context.get('scope', 'general')

            # Try to load in the certificate in different format starting with DER then PKCS12 and
            # finally PEM. If none succeeded, we raise an error.
            try:
                cert = x509.load_der_x509_certificate(content)
                certificate.content_format = 'der'
            except ValueError:
                pass
            if not cert:
                try:
                    pkcs12_password = certificate.pkcs12_password.encode('utf-8') if certificate.pkcs12_password else None
                    key, cert, _additional_certs = pkcs12.load_key_and_certificates(content, pkcs12_password)
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
                certificate.content = None
                raise UserError(_("The certificate could not be loaded."))

            # Extract certificate data
            certificate.pem_certificate = base64.b64encode(cert.public_bytes(Encoding.PEM))
            certificate.date_start = cert.not_valid_before
            certificate.date_end = cert.not_valid_after
            certificate.serial_number = cert.serial_number

            # Create the private key in case of PKCS12 File
            if key:
                certificate.private_key = self.env['certificate.key'].create({
                    'name': (certificate.name or "") + ".key",
                    'content': base64.b64encode(key.private_bytes(
                        encoding=Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    )),
                    'company_id': certificate.company_id.id,
                })

    @api.depends('date_start', 'date_end')
    def _compute_is_valid(self):
        # Certificate dates are UTC timezoned
        # https://cryptography.io/en/latest/x509/reference/#cryptography.x509.Certificate.not_valid_after
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        for certificate in self:
            date_start = certificate.date_start.replace(tzinfo=datetime.timezone.utc)
            date_end = certificate.date_end.replace(tzinfo=datetime.timezone.utc)
            certificate.is_valid = date_start <= utc_now <= date_end

    def _search_is_valid(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        if operator != '=':
            value = not value
        certificates = self.env['certificate.certificate'].search([
            ('company_id', '=', self.env.company.id),
        ]).filtered(lambda cert: cert.is_valid == value)
        return [('id', 'in', certificates.ids)]

    # -------------------------------------------------------
    #                   Business Methods                    #
    # -------------------------------------------------------

    def _get_der_certificate_bytes(self, block=True):
        self.ensure_one()
        pem_certificate = base64.b64decode(self.pem_certificate)
        if block:
            return b"\n".join(pem_certificate.strip().split(b"\n")[1:-1])
        else:
            return b"".join(pem_certificate.strip().split(b"\n")[1:-1])

    def _get_fingerprint_bytes(self, hashing_algorithm='sha256', block=True):
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(_("Unsupported hashing algorithm. Currently supported: sha1 and sha256."))
        if block:
            return base64.encodebytes(cert.fingerprint(STR_TO_HASH[hashing_algorithm]))
        else:
            return base64.b64encode(cert.fingerprint(STR_TO_HASH[hashing_algorithm]))

    def _get_signature_bytes(self, block=True):
        self.ensure_one()
        cert = x509.load_pem_x509_certificate(base64.b64decode(self.pem_certificate))
        if block:
            return base64.encodebytes(cert.signature)
        else:
            return base64.b64encode(cert.signature)

    def _get_public_key_numbers_bytes(self, block=True):
        self.ensure_one()
        if not self.private_key:
            raise UserError(_("There is no private key linked to the certificate."))
        return self.private_key._get_public_key_numbers_bytes(block)

    def _get_public_key_bytes(self, encoding='der', block=True):
        self.ensure_one()
        if not self.private_key:
            raise UserError(_("There is no private key linked to the certificate."))
        return self.private_key._get_public_key_bytes(encoding=encoding, block=block)

    def _sign(self, message, hashing_algorithm='sha256', block=True):
        """ Return the base64 encoded signature of message. """
        self.ensure_one()

        if not self.is_valid:
            raise UserError(_("This certificate is not valid, its validity has probably expired"))
        if not self.private_key:
            raise UserError(_("No private key linked to the certificate, it is required to sign documents"))

        return self.private_key._sign(message, hashing_algorithm=hashing_algorithm, block=block)

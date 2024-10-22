import base64
import textwrap

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import format_datetime
from odoo.tools.osutil import clean_filename

URL_FAQ = "https://cryptography.io/en/latest/faq.html#why-can-t-i-import-my-pem-file"


class BaseX509Wizard(models.TransientModel):
    _name = 'base.x509.wizard'
    _description = "x509 Certificate Import Wizard"

    certificate_pem = fields.Binary("PEM Certificate", required=True,
        help="The PEM-encoded x509 certificate of the organisation.")
    public_key_pem = fields.Binary("PEM Public Key", compute='_compute_certificate_info',
        help="The PEM-encoded public key used by the organisation.")
    subject = fields.Char("Subject", compute='_compute_certificate_info',
        help="The organisation for which this certificate was issued.")
    subject_alternative_names = fields.Char("Subject Alternative Names", compute='_compute_certificate_info',
        help="Alternative names (usually domain names) of the organisation.")
    issuer = fields.Char("Issuer", compute='_compute_certificate_info',
        help="The certification authority (CA) that issued the certificate.")
    not_valid_before = fields.Datetime("Not valid before", compute='_compute_certificate_info',
        help="Date before which the certificate is not yet valid.")
    not_valid_after = fields.Datetime("Not valid after", compute='_compute_certificate_info',
        help="Date after which the certificate is not valid anymore.")
    signature = fields.Char("Signature", compute='_compute_certificate_info',
        help="The digital fingerprint of the certificate, signed by the certification authority.")
    filename = fields.Char("Filename", compute='_compute_certificate_info')

    @api.depends('certificate_pem')
    def _compute_certificate_info(self):
        self = self.with_context(bin_size=False)
        for record in self:
            if not record.certificate_pem:
                record.public_key_pem = False
                record.subject = False
                record.subject_alternative_names = False
                record.issuer = False
                record.not_valid_before = False
                record.not_valid_after = False
                record.signature = False
                record.filename = False
                continue

            certpem = base64.b64decode(record.certificate_pem)
            try:
                cert = x509.load_pem_x509_certificate(certpem)
            except ValueError as exc:
                record.certificate_pem = False
                msg = _("Unable to load certificate. See %(url)s for more details.", url=URL_FAQ)
                raise UserError(msg) from exc

            record.public_key_pem = base64.b64encode(cert.public_key().public_bytes(
                Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
            record.subject = cert.subject.rfc4514_string()
            record.issuer = cert.issuer.rfc4514_string()
            record.not_valid_before = cert.not_valid_before  # _utc.replace(tzinfo=None)
            record.not_valid_after = cert.not_valid_after  # _utc.replace(tzinfo=None)

            # replicates openssl x509 -text behavior, for easy comparison
            record.signature = '\n'.join(textwrap.wrap(cert.signature.hex(sep=':'), 54))

            try:
                san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            except x509.ExtensionNotFound:
                record.subject_alternative_names = ''
            else:
                record.subject_alternative_names = ', '.join(
                    san.value.get_values_for_type(x509.DNSName) +
                    san.value.get_values_for_type(x509.IPAddress))

            common_names = [
                common_name.value
                for common_name
                in cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
                if common_name.value
            ]
            if not common_names:
                common_names = list(filter(bool, self.subject_alternative_names.split(', ')))
            if not common_names:
                common_names = [record.subject]
            record.filename = clean_filename(f'{common_names[0]}.pub.pem')

    def _save(self):
        self.ensure_one()

        public_key = self.env['ir.attachment'].create({
            'name': self.filename,
            'mimetype': 'application/x-pem-file',
            'datas': self.public_key_pem,
            'description': _(
                "This public key was extracted from the following certificate.\n"
                "\n"
                "Subject: %(subject)s\n"
                "Subject alternative names: %(subject_alternative_names)s\n"
                "Issuer: %(issuer)s\n"
                "Not valid before: %(not_valid_before)s\n"
                "Not valid after: %(not_valid_after)s\n"
                "Signature:\n"
                "%(signature)s\n",
                subject=self.subject,
                subject_alternative_names=self.subject_alternative_names,
                issuer=self.issuer,
                not_valid_before=format_datetime(self.env, self.not_valid_before),
                not_valid_after=format_datetime(self.env, self.not_valid_after),
                signature=self.signature,
            )
        })

        return public_key

    def save(self):
        raise NotImplementedError  # abstract method


class BaseX509mailWizard(models.TransientModel):
    _name = 'base.x509mail.wizard'
    _inherit = 'base.x509.wizard'
    _description = "x509 Certificate Import Wizard for Mail Server"

    mail_server_id = fields.Many2one('ir.mail_server', required=True)

    def save(self):
        public_key = self._save()
        self.mail_server_id.smtp_ssl_trusted_public_keys += public_key

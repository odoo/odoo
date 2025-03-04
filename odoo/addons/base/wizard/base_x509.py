import base64
import contextlib
import itertools
import re
import smtplib
import socket
import ssl
import textwrap

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from OpenSSL.SSL import Error as SSLError

try:
    # urllib3 1.26 (ubuntu jammy and up, debian bullseye and up)
    from urllib3.util.ssl_match_hostname import CertificateError
except ImportError:
    # urllib3 1.25 and below
    from urllib3.packages.ssl_match_hostname import CertificateError

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import format_datetime
from odoo.tools.osutil import clean_filename

from odoo.addons.base.models.ir_mail_server import SMTP_TIMEOUT

URL_FAQ = "https://cryptography.io/en/latest/faq.html#why-can-t-i-import-my-pem-file"


class BaseX509Wizard(models.TransientModel):
    _name = 'base.x509.wizard'
    _description = "x509 Certificate Import Wizard"

    certificate_pem = fields.Binary(
        string="PEM Certificate",
        required=True,
        help="The PEM-encoded x509 certificate of the organisation.")

    # Extracted from the certificate
    public_key_pem = fields.Binary(
        string="PEM Public Key",
        compute='_compute_certificate_info',
        help="The PEM-encoded public key used by the organisation.")
    subject = fields.Char(
        string="Subject",
        compute='_compute_certificate_info',
        help="The organisation for which this certificate was issued.")
    subject_alternative_names = fields.Char(
        string="Subject Alternative Names",
        compute='_compute_certificate_info',
        help="Alternative names (usually domain names) of the organisation.")
    issuer = fields.Char(
        string="Issuer",
        compute='_compute_certificate_info',
        help="The certification authority (CA) that issued the certificate.")
    not_valid_before = fields.Datetime(
        string="Not valid before",
        compute='_compute_certificate_info',
        help="Date before which the certificate is not yet valid.")
    not_valid_after = fields.Datetime(
        string="Not valid after",
        compute='_compute_certificate_info',
        help="Date after which the certificate is not valid anymore.")
    signature = fields.Char(
        string="Signature",
        compute='_compute_certificate_info',
        help="The digital fingerprint of the certificate, signed by the certification authority.")
    filename = fields.Char(
        string="Filename",
        compute='_compute_certificate_info',
        help="The filename of the attachment, may the certificate be saved.")

    # Where to save the attachment, may the user clicks the save() button on the wizard.
    mail_server_id = fields.Many2one('ir.mail_server', required=False)

    @api.depends('certificate_pem')
    def _compute_certificate_info(self):
        self = self.with_context(bin_size=False)  # noqa: PLW0642
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

            common_name = next(itertools.chain(
                (common_name.value
                 for common_name
                 in cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
                 if common_name.value),
                (alternative_name
                 for alternative_name
                 in self.subject_alternative_names.split(', ')
                 if alternative_name),
                (record.subject,),
            ))
            record.filename = clean_filename(f'{common_name}.pub.pem')

    def save(self):
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
        if self.mail_server_id:
            self.mail_server_id.smtp_ssl_trusted_public_keys += public_key
        return public_key

    def download(self):
        if self.mail_server_id:
            return self._download_from_mail_server()
        raise UserError(_("Cannot download the certificate of an unknown server."))

    def _download_from_mail_server(self):
        try:
            self.mail_server_id.test_smtp_connection()
        except UserError as e:
            pattern = r"|".join((
                r"certificate verify failed",
                r"Hostname mismatch, certificate is not valid for '.*?'",
                r"hostname '.*' doesn't match '.*?'",
            ))  # noqa: FLY002
            if not isinstance(e.__cause__, (ssl.SSLError, SSLError, CertificateError)):
                raise
            if not re.search(pattern, str(e.__cause__)):
                raise
        else:
            raise UserError(_("The connection can be established already. Certificate importation cancelled."))

        # re-establish a secure connection, this time accepting any certificate
        # and download the remote certificate
        with contextlib.ExitStack() as stack:
            if self.mail_server_id.smtp_encryption == 'starttls':
                conn = stack.enter_context(
                    smtplib.SMTP(self.mail_server_id.smtp_host, self.mail_server_id.smtp_port, timeout=SMTP_TIMEOUT))
                conn.docmd("STARTTLS")
                sock = conn.sock
            else:
                assert self.mail_server_id.smtp_encryption == 'ssl'
                sock = stack.enter_context(socket.create_connection(
                    (self.mail_server_id.smtp_host, self.mail_server_id.smtp_port), timeout=SMTP_TIMEOUT))

            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            with ssl_context.wrap_socket(sock) as ssock:
                certder = ssock.getpeercert(binary_form=True)

        self.write({
            'certificate_pem': base64.b64encode(ssl.DER_cert_to_PEM_cert(certder).encode())
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _("Security Exception - Add a trusted public key"),
            'target': 'new',
            'res_model': self._name,
            'res_id': self.id,
            'views': [(False, 'form')],
        }

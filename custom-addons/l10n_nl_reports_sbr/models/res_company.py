# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, _
from odoo.exceptions import UserError, RedirectWarning
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from datetime import datetime
import base64
import requests

class ResCompany(models.Model):

    _inherit = "res.company"

    l10n_nl_reports_sbr_cert = fields.Binary(
        'PKI Certificate',
        groups="base.group_system",
        help="Upload here the certificate file that will be used to connect to the Digipoort infrastructure. "
             "The private key from this file will be used, if there is one included.",
    )
    l10n_nl_reports_sbr_key = fields.Binary(
        'PKI Private Key',
        groups="base.group_system",
        help="A private key is required in order for the Digipoort services to identify you. "
             "No need to upload a key if it is already included in the certificate file.",
    )
    l10n_nl_reports_sbr_cert_filename = fields.Char('Certificate File Name')
    l10n_nl_reports_sbr_key_filename = fields.Char('Private Key File Name')
    l10n_nl_reports_sbr_server_root_cert = fields.Binary(
        'SBR Root Certificate',
        help="The SBR Tax Service Server Root Certificate is used to verifiy the connection with the Tax services server of the SBR."
        "It is used in order to make the connection library trust the server."
    )
    l10n_nl_reports_sbr_last_sent_date_to = fields.Date(
        'Last Date Sent',
        help="Stores the date of the end of the last period submitted to the Tax Services",
        readonly=True
    )

    def _l10n_nl_get_certificate_and_key_bytes(self, password=None):
        """ Return the tuple (certificate, private key), each in the form of unencrypted PEM encoded bytes.
            Parameter password must be a bytes object or None.
            Throws a UserError if there is a misconfiguration.
        """
        self.ensure_one()

        if not self.l10n_nl_reports_sbr_cert or not self.l10n_nl_reports_sbr_key:
            raise RedirectWarning(
                _("The certificate or the private key is missing. Please upload it in the Accounting Settings first."),
                self.env.ref('account.action_account_config').id,
                _("Go to the Accounting Settings"),
            )
        stored_certificate = base64.b64decode(self.l10n_nl_reports_sbr_cert)
        stored_key = base64.b64decode(self.l10n_nl_reports_sbr_key)

        try:
            cert_obj, pkey_obj = (x509.load_pem_x509_certificate(stored_certificate), serialization.load_pem_private_key(stored_key, password or None))
        except TypeError:
            raise UserError(_('The certificate or private key you uploaded is encrypted. Please specify your password.'))
        except ValueError:
            raise UserError(_('An error occurred while decrypting your certificate or private key. Please verify your password.'))

        cert_bytes = cert_obj.public_bytes(serialization.Encoding.PEM)
        pkey_bytes = pkey_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return (cert_bytes, pkey_bytes)

    def _l10n_nl_get_server_root_certificate_bytes(self):
        """ Return the tax service server root certificate as PEM encoded bytes.
            Throws a UserError if the services are not reachable.
        """
        cert_root_bytes = base64.b64decode(self.l10n_nl_reports_sbr_server_root_cert or '')
        if not cert_root_bytes or x509.load_pem_x509_certificate(cert_root_bytes).not_valid_after < datetime.now():
            try:
                req_root = requests.get('https://cert.pkioverheid.nl/PrivateRootCA-G1.cer', timeout=30)
                req_root.raise_for_status()

                # This certificate is a .cer and is in DER format, we need to change it to PEM format for the libraries
                der_root_obj = x509.load_der_x509_certificate(req_root.content)
                cert_root_bytes = der_root_obj.public_bytes(serialization.Encoding.PEM)
                self.l10n_nl_reports_sbr_server_root_cert = base64.b64encode(cert_root_bytes)
            except:
                raise UserError(_("The server root certificate is not accessible at the moment. Please try again later."))
        return cert_root_bytes

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12, pkcs7
from cryptography import x509
import base64

class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_nl_reports_sbr_key = fields.Binary(related='company_id.l10n_nl_reports_sbr_key', readonly=False)
    l10n_nl_reports_sbr_cert = fields.Binary(related='company_id.l10n_nl_reports_sbr_cert', readonly=False)

    l10n_nl_reports_sbr_cert_filename = fields.Char(related='company_id.l10n_nl_reports_sbr_cert_filename')
    l10n_nl_reports_sbr_key_filename = fields.Char(related='company_id.l10n_nl_reports_sbr_key_filename')
    l10n_nl_reports_sbr_password = fields.Char('Certificate/key password')

    def _l10n_nl_reports_sbr_load_certificate(self, certificate, password):
        """ Check and transform the uploaded certificate into PEM format.
            If the certificate file also contains the key, it will be extracted and returned in PEM format as well.
        """
        if not certificate:
            return certificate, False

        stored_cert = base64.b64decode(certificate)

        # This succession of try - except is needed as the cryptography library does not offer
        # a filetype checking function nor a general loading function.
        # The only way to load the correct type is to test them all (PEM, DER, PKCS7 PEM, PKCS7 DER and then PKCS12),
        # one at a time, until we get the right one or an error is finally raised
        try:
            # PEM format
            x509.load_pem_x509_certificate(stored_cert)
            return certificate, False
        except ValueError:
            password
        try:
            # DER format
            der_cert = x509.load_der_x509_certificate(stored_cert)
            return base64.b64encode(der_cert.public_bytes(serialization.Encoding.PEM)), False
        except ValueError:
            pass
        try:
            # PKCS7 can be stored as either PEM or DER format.
            # PKCS7 file PEM format
            pkcs7_pem_cert = pkcs7.load_pem_pkcs7_certificates(stored_cert)[0]
            return base64.b64encode(pkcs7_pem_cert.public_bytes(serialization.Encoding.PEM)), False
        except ValueError:
            pass
        try:
            # PKCS7 file DER format
            pkcs7_der_cert = pkcs7.load_der_pkcs7_certificates(stored_cert)[0]
            return base64.b64encode(pkcs7_der_cert.public_bytes(serialization.Encoding.PEM)), False
        except ValueError:
            pass
        try:
            # A PKCS12 file can also contain the private key (unlike the other types),
            # which is why a password might be needed for decryption.
            # We want the key to stay encrypted with the password.
            private_key, pkcs12_cert, _additional_certs = pkcs12.load_key_and_certificates(stored_cert, bytes(password or '', 'utf-8'))
            encryption = serialization.BestAvailableEncryption(bytes(password, 'utf-8')) if password else serialization.NoEncryption()
            key = base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption,
            ))
            return base64.b64encode(pkcs12_cert.public_bytes(serialization.Encoding.PEM)), key
        except ValueError:
            raise ValidationError(_("An error occurred while loading the certificate. Please check the uploaded file and the related password."))

    def _l10n_nl_reports_sbr_load_key(self, key, password):
        """ Check and transform the uploaded private key into PEM format.
        """
        if not key:
            return key
        stored_key = base64.b64decode(key)
        pwd = bytes(password or '', 'utf-8')

        # As for the certificates, cryptography does not provide a simple general function for key decryption.
        # We need to test each type (PEM or DER).
        try:
            # PEM format
            serialization.load_pem_private_key(stored_key, pwd or None)
            return key
        except ValueError:
            try:
                # DER format
                # As PEM is the format used for the other libraries of the modules,
                # we prefer to change its format from DER to PEM, if needed, while keeping its password encryption.
                der_key = serialization.load_der_private_key(stored_key, pwd or None)
                encryption = serialization.BestAvailableEncryption(bytes(password, 'utf-8')) if password else serialization.NoEncryption()
                return base64.b64encode(der_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=encryption,
                ))
            except ValueError:
                raise ValidationError(_('The provided key could not be successfully loaded.'))
            except TypeError:
                raise ValidationError(_('The provided password for the key is not correct.'))
        except TypeError:
            raise ValidationError(_('The provided password for the key is not correct.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            password = vals.get('l10n_nl_reports_sbr_password')
            certificate = bytes(vals.get('l10n_nl_reports_sbr_cert') or '', 'UTF-8')
            private_key = bytes(vals.get('l10n_nl_reports_sbr_key') or '', 'UTF-8')

            if self.env.company.l10n_nl_reports_sbr_cert != certificate:
                certificate, key = self._l10n_nl_reports_sbr_load_certificate(certificate, password)
                if key:
                    private_key = key
            if self.env.company.l10n_nl_reports_sbr_key != private_key:
                private_key = self._l10n_nl_reports_sbr_load_key(private_key, password)

            if bool(certificate) != bool(private_key):
                raise ValidationError(_('The certificate or private key for SBR services is missing.'))
            vals['l10n_nl_reports_sbr_cert'] = certificate
            vals['l10n_nl_reports_sbr_key'] = private_key
        return super(ResConfigSettings, self).create(vals_list)

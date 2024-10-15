from cryptography.fernet import Fernet

from odoo import api, models
from odoo.addons import certificate


class CertificateKey(certificate.CertificateKey):

    @api.model
    def _account_edi_fernet_decrypt(self, key, message):
        key = Fernet(key)
        return key.decrypt(message)

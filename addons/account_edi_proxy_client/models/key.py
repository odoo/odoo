from cryptography.fernet import Fernet

from odoo import api, models


class Key(models.Model):
    _inherit = 'certificate.key'

    @api.model
    def _fernet_decrypt(self, key, message):
        key = Fernet(key)
        return key.decrypt(message)

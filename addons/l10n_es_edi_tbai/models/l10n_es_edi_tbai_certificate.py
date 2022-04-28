# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from datetime import datetime
from OpenSSL import crypto

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from odoo import api, models
from pytz import timezone


class Certificate(models.Model):
    _inherit = 'l10n_es_edi.certificate'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _get_es_current_datetime(self):
        """Get the current datetime with the Basque timezone. """
        # oVERRIDE
        return datetime.now(timezone('Europe/Madrid'))

    def _get_key_pair(self):
        self.ensure_one()

        if not self.password:
            return None, None

        private_key, certificate, dummy = pkcs12.load_key_and_certificates(
            b64decode(self.with_context(bin_size=False).content),  # Without bin_size=False, size is returned instead of content
            self.password.encode(),
            backend=default_backend(),
        )

        return private_key, certificate

    def _get_p12(self):
        # Cryptography's pkcs12 does not contain issuer data ? TODO alternative without OpenSSL
        return crypto.load_pkcs12(b64decode(self.with_context(bin_size=False).content), self.password.encode())

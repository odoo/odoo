# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from odoo import models


class Certificate(models.Model):
    _inherit = 'l10n_es_edi.certificate'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

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

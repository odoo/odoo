# -*- coding: utf-8 -*-
from odoo.addons import l10n_es_edi_sii
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode

from odoo import models
from odoo.addons.account.tools.certificate import load_key_and_certificates


class L10nEsEdiCertificate(models.Model, l10n_es_edi_sii.L10nEsEdiCertificate):
    _name = "l10n_es_edi.certificate"


    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_key_pair(self):
        self.ensure_one()

        if not self.password:
            return None, None

        private_key, certificate = load_key_and_certificates(
            b64decode(self.with_context(bin_size=False).content),  # Without bin_size=False, size is returned instead of content
            self.password.encode(),
        )

        return private_key, certificate

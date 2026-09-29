# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models


siren_siret_re = re.compile(r'^(\d{9}|\d{14})$')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_fr_get_siren(self):

        siret = self.siret or (self.company_registry if self.company_registry and siren_siret_re.match(self.company_registry) else '')
        if len(siret) >= 9:
            return siret[:9]
        return False

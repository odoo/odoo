# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_es_get_pos_edi_mode(self):
        self.ensure_one()
        return 'verifactu' if self.l10n_es_edi_verifactu_required else super()._l10n_es_get_pos_edi_mode()

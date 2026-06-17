# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_es_get_pos_edi_mode(self):
        """Return the POS EDI mode for this company.
        Returns 'tbai', 'verifactu', or False (standard session closing entry).
        """
        self.ensure_one()
        return False

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _has_l10n_de_stnr(self):
        """ Whether this is a DE company with a Steuernummer (BT-32) set. """
        self.ensure_one()
        return (
            self.country_code == 'DE'
            and bool('l10n_de_stnr' in self._fields and self.l10n_de_stnr)
        )

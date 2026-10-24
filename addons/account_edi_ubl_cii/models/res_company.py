from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_l10n_de_stnr(self):
        """ The Steuernummer (BT-32) of a DE company, or False. """
        self.ensure_one()
        # l10n_de is not a dependency: use item access since the field may not exist.
        if self.country_code == 'DE' and 'l10n_de_stnr' in self._fields:
            return self['l10n_de_stnr']
        return False

from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_l10n_latam_base_country_codes(self):
        # EXTENDS 'l10n_latam_base' - adds CO
        return super()._get_l10n_latam_base_country_codes() + ['CO']

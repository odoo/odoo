# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _display_partner_b2b_fields(self):
        """ Brazil localization must always display b2b fields. """
        return self.company_id.country_id.code == 'BR' or super()._display_partner_b2b_fields()

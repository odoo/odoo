from odoo import models


class Website(models.Model):
    _inherit = 'website'

    def _display_partner_b2b_fields(self):
        """Spanish localization must always display B2B fields."""
        self.ensure_one()
        return self.company_id.country_id.code == "ES" or super()._display_partner_b2b_fields()

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CountryState(models.Model):
    _inherit = "res.country.state"

    def get_website_sale_cities(self, mode="billing"):
        return self.env["res.city"].search([("state_id", "=", self.id)])

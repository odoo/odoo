# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class City(models.Model):
    _inherit = "res.city"

    def get_website_sale_districts(self, mode="billing"):
        return self.env["l10n_pe.res.city.district"].search([("city_id", "=", self.id)])

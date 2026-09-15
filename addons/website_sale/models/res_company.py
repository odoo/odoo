from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _prepare_default_pricelist_vals(self):
        values = super()._prepare_default_pricelist_vals()
        values["website_id"] = False
        return values

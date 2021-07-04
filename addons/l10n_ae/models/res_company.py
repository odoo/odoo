from odoo import models, api
from ..tools import create_journals


class Company(models.Model):
    _inherit = "res.company"

    @api.model
    def create(self, vals_list):
        res = super(Company, self).create(vals_list)
        if vals_list.get("country_id") and res.country_id.code == "AE":
            create_journals(self.sudo().env)
        return res

    def write(self, vals):
        res = super(Company, self).write(vals)
        if vals.get("country_id") and self.country_id.code == "AE":
            create_journals(self.sudo().env)
        return res

from odoo import models, api
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import create_journals

JOURNAL_TO_CREATE = [{"code": "TA", "name": "Tax Adjustments", "type": "general"},
                      {"code": "IFRS", "name": "IFRS 16", "type": "general"}]


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

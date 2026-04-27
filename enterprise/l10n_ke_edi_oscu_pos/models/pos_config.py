from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    is_kenyan = fields.Boolean(string="Company located in Kenya", compute="_compute_is_kenyan")

    @api.depends("company_id")
    def _compute_is_kenyan(self):
        for pos in self:
            pos.is_kenyan = pos.company_id.country_code == "KE"

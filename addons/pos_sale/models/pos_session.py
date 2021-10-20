# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    crm_team_id = fields.Many2one('crm.team', related='config_id.crm_team_id', string="Sales Team", readonly=True)

    def _loader_info_product_product(self):
        result = super(PosSession, self)._loader_info_product_product()
        result["domain"] = OR([result["domain"], [("id", "=", self.config_id.down_payment_product_id.id)]])
        result["fields"].extend(["invoice_policy", "type"])
        return result

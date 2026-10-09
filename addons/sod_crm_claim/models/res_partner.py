# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _compute_claim_count(self):
        claim_obj = self.env["crm.claim"]
        for partner in self:
            partner.claim_count = claim_obj.search_count(
                [
                    "|",
                    ("partner_id", "in", partner.commercial_partner_id.child_ids.ids),
                    ("partner_id", "=", partner.id),
                ]
            )

    claim_count = fields.Integer(compute="_compute_claim_count", string="# Returns")

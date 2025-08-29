# Copyright 2024 ForgeFlow S.L. (http://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    signer_ids = fields.One2many(
        comodel_name="sign.oca.request.signer", inverse_name="partner_id"
    )
    signer_count = fields.Integer(compute="_compute_signers_count")

    def _compute_signers_count(self):
        for rec in self:
            rec.signer_count = len(rec.signer_ids)

    def action_show_signer_ids(self):
        self.ensure_one()
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "sign_oca.sign_oca_request_signer_act_window"
        )
        result["domain"] = [("id", "in", self.signer_ids.ids)]
        return result

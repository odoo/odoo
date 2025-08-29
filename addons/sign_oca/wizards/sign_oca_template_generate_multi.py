# Copyright 2023-2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SignOcaTemplateGenerateMulti(models.TransientModel):
    _name = "sign.oca.template.generate.multi"
    _description = "Generate signature requests"

    model = fields.Char(
        readonly=True, default=lambda self: self.env.context.get("model", False)
    )
    template_id = fields.Many2one(
        comodel_name="sign.oca.template",
        domain="[('model', '=', model)]",
        required=True,
    )
    message = fields.Html()

    def _prepare_sign_oca_request_vals(self):
        vals = []
        for item in self.env[self.model].browse(self.env.context.get("active_ids")):
            vals.append(
                self.template_id._prepare_sign_oca_request_vals_from_record(item)
            )
        return vals

    def _generate(self):
        return self.env["sign.oca.request"].create(
            self._prepare_sign_oca_request_vals()
        )

    def generate(self):
        requests = self._generate()
        for request in requests:
            request.action_send(message=self.message)
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "sign_oca.sign_oca_request_act_window"
        )
        action["domain"] = [("id", "in", requests.ids)]
        return action

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class RentalOrder(models.Model):
    _inherit = "sale.order"

    sign_request_ids = fields.One2many("sign.request", string="Signature Requests", compute="_compute_sign_request")
    sign_request_count = fields.Integer(
        "# of Signature Requests", compute="_compute_sign_request"
    )

    def _compute_sign_request(self):
        ref_values = [f"sale.order,{rec.id}" for rec in self]
        sign_data = self.env["sign.request"]._read_group(
            domain=[('reference_doc', 'in', ref_values)],
            groupby=['reference_doc'],
            aggregates=['id:recordset'],
        )
        self.sign_request_ids = False
        self.sign_request_count = 0
        # We group the sign requests by orders
        for dummy, sign_requests in sign_data:
            order = sign_requests[:1].reference_doc
            order.sign_request_ids = [Command.set(sign_requests.ids)]
            order.sign_request_count = len(sign_requests)

    def action_view_sign(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sign.sign_request_action")
        # action["context"] = {"create": False}
        if self.sign_request_count > 1:
            ref_values = [f"sale.order,{rec.id}" for rec in self]
            action["domain"] = [('reference_doc', 'in', ref_values)]
        elif self.sign_request_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.sign_request_ids.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

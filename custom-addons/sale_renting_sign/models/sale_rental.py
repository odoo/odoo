# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class RentalOrder(models.Model):
    _inherit = "sale.order"

    sign_request_ids = fields.One2many(
        "sign.request", "sale_order_id", string="Signature Requests"
    )
    sign_request_count = fields.Integer(
        "# of Signature Requests", compute="_compute_sign_request_count"
    )

    def _compute_sign_request_count(self):
        sign_data = self.env["sign.request"]._read_group(
            domain=[("sale_order_id", "in", self.ids)],
            groupby=['sale_order_id'],
            aggregates=['__count'],
        )
        mapped_data = {sale_order.id: count for sale_order, count in sign_data}
        for order in self:
            order.sign_request_count = mapped_data.get(order.id, 0)

    def action_view_sign(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sign.sign_request_action")
        # action["context"] = {"create": False}
        if len(self.sign_request_ids) > 1:
            action["domain"] = [("sale_order_id", "=", self.id)]
        elif len(self.sign_request_ids) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.sign_request_ids.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

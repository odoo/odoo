# Copyright (C) 2018, Open Source Integrators
# Copyright 2019 Akretion <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    fsm_order_ids = fields.Many2many(
        "fsm.order",
        compute="_compute_fsm_order_ids",
        string="Field Service orders associated to this invoice",
    )
    fsm_order_count = fields.Integer(
        string="FSM Orders", compute="_compute_fsm_order_ids"
    )

    @api.depends("line_ids")
    def _compute_fsm_order_ids(self):
        for record in self:
            orders = self.env["fsm.order"].search(
                [("invoice_lines", "in", record.line_ids.ids)]
            )
            record.fsm_order_ids = orders
            record.fsm_order_count = len(record.fsm_order_ids)

    def action_view_fsm_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "fieldservice.action_fsm_dash_order"
        )
        if self.fsm_order_count > 1:
            action["domain"] = [("id", "in", self.fsm_order_ids.ids)]
        elif self.fsm_order_ids:
            action["views"] = [(self.env.ref("fieldservice.fsm_order_form").id, "form")]
            action["res_id"] = self.fsm_order_ids[0].id
        return action

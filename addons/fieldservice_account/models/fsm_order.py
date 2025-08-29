# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    invoice_lines = fields.Many2many(
        "account.move.line",
        "fsm_order_account_move_line_rel",
        "fsm_order_id",
        "account_move_line_id",
        copy=False,
    )

    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        compute="_compute_get_invoiced",
        readonly=True,
        copy=False,
    )

    invoice_count = fields.Integer(
        compute="_compute_get_invoiced",
        readonly=True,
        copy=False,
    )

    @api.depends("invoice_lines")
    def _compute_get_invoiced(self):
        for order in self:
            invoices = order.invoice_lines.mapped("move_id").filtered(
                lambda r: r.move_type in ("out_invoice", "out_refund")
            )
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        invoices = self.mapped("invoice_ids")
        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif invoices:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.ids[0]
        return action

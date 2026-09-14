from odoo import Command, _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class InvoiceToSoWizard(models.TransientModel):
    _name = "invoice.to.so.wizard"
    _description = "Customer Invoice to Sales Order"

    sale_order_id = fields.Many2one(comodel_name="sale.order")
    partner_id = fields.Many2one(comodel_name="res.partner")

    def action_add_to_so(self):
        aml_ids = [
            abs(record_id)
            for record_id in (self.env.context.get("active_ids") or [])
            if record_id < 0
        ]
        lines_to_add = (
            self.env["account.move.line"]
            .browse(aml_ids)
            .filtered(lambda line: line.product_id)
        )
        if not lines_to_add:
            _debug.logic(
                "invoice_to_so_refused", wizard=self, reason="no_product_lines"
            )
            raise UserError(_("There are no products to add to the Sales Order."))
        line_vals = lines_to_add._sale_prepare_order_line_values()
        if self.sale_order_id:
            new_order_lines = self.env["sale.order.line"].create(
                [
                    {
                        **vals,
                        "order_id": self.sale_order_id.id,
                    }
                    for vals in line_vals
                ]
            )
            self.sale_order_id.line_ids += new_order_lines
            _debug.lifecycle(
                "invoice_lines_added_to_order",
                order=self.sale_order_id,
                lines=new_order_lines,
            )
        else:
            self.sale_order_id = self.env["sale.order"].create(
                {
                    "partner_id": lines_to_add.partner_id.id,
                    "line_ids": [Command.create(vals) for vals in line_vals],
                }
            )
            new_order_lines = self.sale_order_id.line_ids
            _debug.lifecycle(
                "order_created_from_invoice_lines",
                order=self.sale_order_id,
                lines=new_order_lines,
            )

        if self.sale_order_id.state == "draft":
            _debug.pipeline("confirm_after_invoice_match", order=self.sale_order_id)
            self.sale_order_id.action_confirm()
        for aml, order_line in zip(lines_to_add, new_order_lines, strict=False):
            if aml.product_id == order_line.product_id:
                aml.sale_line_ids = [Command.link(order_line.id)]
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": self.sale_order_id.id,
        }

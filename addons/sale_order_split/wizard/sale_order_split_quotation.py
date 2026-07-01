from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrderSplitQuotation(models.TransientModel):
    _name = "sale.order.split.quotation"
    _description = "Split a sale order"

    split_sale_order_options = fields.Selection(
        [
            ("category", "Based on Category"),
            ("selection", "Selected Lines"),
            ("order", "One Line Per Order"),
        ],
        required=True,
    )

    sale_order_line_ids = fields.Many2many(
        "sale.order.line",
    )

    order_ids = fields.Many2many(
        "sale.order",
        default=lambda self: self._default_order_ids(),
    )

    def _default_order_ids(self):
        """This function return the active id of sale order"""
        return self.env["sale.order"].browse(self.env.context.get("active_id"))

    def action_apply(self):
        """This function trigger the split method based on selected option"""
        return getattr(self, "_apply_%s" % self[:1].split_sale_order_options)()

    def _apply_order(self):
        """
        Split sale orders for every sale order line, keep first sale order line
        in original sale order
        """
        new_orders = self.env["sale.order"]
        for order in self.mapped("order_ids"):
            order._check_split_order()
            for line in order.order_line[1:]:
                new_orders |= order._split_order_by_lines(line)
        return self.action_new_orders(new_orders)

    def _apply_selection(self):
        """Split sale order for all selected lines"""
        lines = self.mapped("sale_order_line_ids")
        if not lines:
            raise UserError(
                _("Please select the sale order line which you want to split.")
            )
        new_order = lines.mapped("order_id")._split_order_by_lines(lines)
        return self.action_new_orders(new_order)

    def _apply_category(self):
        """Split sale order based on category of product"""
        new_orders = self.mapped("order_ids")._split_order_by_category()
        return self.action_new_orders(new_orders)

    def action_new_orders(self, new_order):
        """This function open tree or form view of new split sale order"""
        action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_quotations")
        action["domain"] = [("id", "in", new_order.ids)]
        # Open form view if there was only one split order available
        if len(new_order) == 1:
            action["views"] = [(self.env.ref("sale.view_order_form").id, "form")]
            action["res_id"] = new_order.id
        return action

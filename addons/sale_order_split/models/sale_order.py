from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Added new field
    split_sale_order_id = fields.Many2one(
        comodel_name="sale.order", string="Source Order Reference"
    )
    split_order_count = fields.Integer(compute="_compute_split_order_count")

    def _compute_split_order_count(self):
        """This function count the split sale orders"""
        for res in self:
            res.split_order_count = self.env["sale.order"].search_count(
                [("split_sale_order_id", "=", self.id)]
            )

    def action_split_sale_order_quotation(self):
        """
        This function used to trigger the wizard from button with correct context
        """
        return {
            "name": ("Split Sale Order Wizard"),
            "type": "ir.actions.act_window",
            "res_model": "sale.order.split.quotation",
            "view_mode": "form",
            "target": "new",
        }

    def action_split_orders(self):
        """This function open tree and form view of split sale order"""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_quotations")
        action["domain"] = [("split_sale_order_id", "=", self.id)]
        return action

    def _check_split_order(self):
        """This function Check the order state and condition before split"""
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            raise UserError(_("You can't split sale order in %s state!") % (self.state))
        if not len(self.order_line) > 1:
            raise UserError(
                _(
                    "You can't split the sale order as it does not contain an"
                    "appropriate order line."
                )
            )

    def _split_order_by_lines(self, lines):
        """
        This function remove lines from orders in self and put them into
        a new one
        """
        for order in self:
            order._check_split_order()

            split_order = self.env["sale.order"]
            for order in self:
                if not order.order_line - lines:
                    raise UserError(
                        _("You can't split off all lines from order %s") % order.name
                    )
                split_order = order.copy(default={"split_sale_order_id": self.id})
                split_order.write({"order_line": lines})
            return split_order

    def _split_order_by_category(self):
        """
        This function split sale order lines into new sale orders based
        on category
        """
        for order in self:
            order._check_split_order()

            split_order = self.env["sale.order"]
            for order in self:
                categories = order.order_line.mapped("product_id.categ_id")
                if len(categories) == 1:
                    raise UserError(
                        _(
                            "You can't split the sale order as there is only one "
                            "category available."
                        )
                    )
                for category in categories[1:]:
                    order_lines_with_current_category = order.order_line.filtered(
                        lambda line: line.product_id.categ_id == category
                    )
                    new_order = order.copy(
                        default={
                            "split_sale_order_id": self.id,
                            "order_line": [
                                (4, line.id)
                                for line in order_lines_with_current_category
                            ],
                        }
                    )
                    split_order |= new_order
            return split_order

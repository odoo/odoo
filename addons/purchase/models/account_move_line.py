from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    is_downpayment = fields.Boolean()
    purchase_line_ids = fields.Many2many(
        comodel_name="purchase.order.line",
        relation="account_move_line_purchase_order_line_rel",
        column1="move_line_id",
        column2="order_line_id",
        string="Purchase Order Lines",
        copy=False,
    )
    purchase_line_warn_msg = fields.Text(
        compute="_compute_purchase_line_warn_msg",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("product_id.purchase_line_warn_msg")
    def _compute_purchase_line_warn_msg(self):
        has_group = self.env.user.has_group("purchase.group_warning_purchase")
        for line in self:
            line.purchase_line_warn_msg = (
                line.product_id.purchase_line_warn_msg if has_group else ""
            )

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _copy_data_extend_business_fields(self, values):
        super()._copy_data_extend_business_fields(values)
        values["purchase_line_ids"] = [(6, None, self.purchase_line_ids.ids)]

    def _prepare_line_values_for_purchase(self):
        return [
            {
                "product_id": line.product_id.id,
                "product_qty": line.quantity,
                "product_uom_id": line.product_uom_id.id,
                "price_unit": line.price_unit,
                "discount": line.discount,
            }
            for line in self
        ]

    def _related_analytic_distribution(self):
        vals = super()._related_analytic_distribution()
        if self.purchase_line_ids and not self.analytic_distribution:
            vals |= self.purchase_line_ids[0].analytic_distribution or {}
        return vals

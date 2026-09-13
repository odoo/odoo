from odoo import fields, models


class BaseOrderTestLinePriceHistory(models.TransientModel):
    """Concrete `mixin.order.line.price.history`, so its statistics are testable.

    The mixin computes a quantity-weighted average, the extremes and the
    partner-versus-market divergence, over one grouped query when every
    matching line is already in the target currency and row by row when it is
    not. Both shipping wizards live in `sale` and `purchase`, so until this
    existed neither path was asserted anywhere.
    """

    _name = "base.order.test.line.price.history"
    _inherit = ["mixin.order.line.price.history"]
    _description = "Base Order Test Line Price History"

    _price_history_line_model = "base.order.test.line"
    _price_history_action = "test_base_order.action_base_order_test_history"

    line_id = fields.Many2one(
        comodel_name="base.order.test.line",
        string="Target Line",
    )
    line_ids = fields.One2many(
        comodel_name="base.order.test.line.price.history.line",
        inverse_name="wizard_id",
        string="Historical Lines",
    )


class BaseOrderTestLinePriceHistoryLine(models.TransientModel):
    _name = "base.order.test.line.price.history.line"
    _inherit = ["mixin.order.line.price.history.line"]
    _description = "Base Order Test Line Price History Result"

    wizard_id = fields.Many2one(
        comodel_name="base.order.test.line.price.history",
        ondelete="cascade",
    )
    line_id = fields.Many2one(comodel_name="base.order.test.line")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    order_id = fields.Many2one(related="line_id.order_id")
    partner_id = fields.Many2one(related="line_id.partner_id")
    date = fields.Datetime(related="line_id.date_order")
    qty = fields.Float(related="line_id.product_qty")
    product_uom_id = fields.Many2one(related="line_id.product_uom_id")
    price_unit = fields.Float(related="line_id.price_unit")
    discount = fields.Float(related="line_id.discount")
    tax_ids = fields.Many2many(related="line_id.tax_ids")

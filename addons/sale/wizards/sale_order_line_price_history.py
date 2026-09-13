from odoo import fields, models


class SaleOrderLinePriceHistory(models.TransientModel):
    _name = "sale.order.line.price.history"
    _inherit = ["mixin.order.line.price.history"]
    _description = "Sale Order Line Price History"

    _price_history_line_model = "sale.order.line"
    _price_history_action = "sale.action_sale_history"

    line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Target Sale Order Line",
    )
    line_ids = fields.One2many(
        comodel_name="sale.order.line.price.history.line",
        inverse_name="wizard_id",
        string="Historical Sale Lines",
    )
    partner_id = fields.Many2one(string="Customer")
    include_draft = fields.Boolean(string="Include Quotations")


class SaleOrderLinePriceHistoryLine(models.TransientModel):
    _name = "sale.order.line.price.history.line"
    _inherit = ["mixin.order.line.price.history.line"]
    _description = "Sale Order Line Price History Result"

    wizard_id = fields.Many2one(
        comodel_name="sale.order.line.price.history",
        ondelete="cascade",
    )
    line_id = fields.Many2one(comodel_name="sale.order.line")
    currency_id = fields.Many2one(related="wizard_id.currency_id")
    order_id = fields.Many2one(related="line_id.order_id")
    partner_id = fields.Many2one(
        related="line_id.partner_id",
        string="Customer",
    )
    date = fields.Datetime(related="line_id.date_order")
    qty = fields.Float(related="line_id.product_qty")
    product_uom_id = fields.Many2one(related="line_id.product_uom_id")
    price_unit = fields.Float(related="line_id.price_unit")
    discount = fields.Float(related="line_id.discount")
    tax_ids = fields.Many2many(related="line_id.tax_ids")

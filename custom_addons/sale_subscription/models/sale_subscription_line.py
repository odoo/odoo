from odoo import api, fields, models


class SaleSubscriptionLine(models.Model):
    _name = "sale.subscription.line"
    _description = "Subscription Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    subscription_id = fields.Many2one(
        comodel_name="sale.subscription",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="subscription_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="subscription_id.currency_id",
        store=True,
        readonly=True,
    )
    name = fields.Char(required=True)
    product_id = fields.Many2one(
        comodel_name="product.product",
        domain=[("sale_ok", "=", True)],
        ondelete="restrict",
    )
    quantity = fields.Float(default=1.0, required=True)
    price_unit = fields.Monetary(default=0.0, required=True, currency_field="currency_id")
    discount = fields.Float(default=0.0, string="Discount (%)")
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        relation="sale_subscription_line_tax_rel",
        column1="line_id",
        column2="tax_id",
        string="Taxes",
    )
    price_subtotal = fields.Monetary(
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )
    price_tax = fields.Monetary(
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )
    price_total = fields.Monetary(
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )

    @api.depends(
        "quantity",
        "price_unit",
        "discount",
        "tax_ids",
        "subscription_id.partner_id",
        "currency_id",
    )
    def _compute_amount(self):
        for line in self:
            quantity = line.quantity or 0.0
            unit = line.price_unit or 0.0
            discount = line.discount or 0.0
            discounted_unit = unit * (1.0 - (discount / 100.0))
            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    discounted_unit,
                    currency=line.currency_id,
                    quantity=quantity,
                    product=line.product_id,
                    partner=line.subscription_id.partner_id,
                )
                line.price_subtotal = taxes["total_excluded"]
                line.price_total = taxes["total_included"]
                line.price_tax = taxes["total_included"] - taxes["total_excluded"]
            else:
                subtotal = discounted_unit * quantity
                line.price_subtotal = subtotal
                line.price_total = subtotal
                line.price_tax = 0.0


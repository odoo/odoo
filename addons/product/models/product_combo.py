from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductCombo(models.Model):
    _name = "product.combo"
    _description = "Product Combo"
    _order = "sequence, id"

    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
    )
    name = fields.Char(required=True)
    sequence = fields.Integer(
        default=10,
        copy=False,
    )
    combo_item_ids = fields.One2many(
        comodel_name="product.combo.item",
        inverse_name="combo_id",
        copy=True,
    )
    count_combo_item_ids = fields.Integer(
        string="Product Count",
        compute="_compute_count_combo_item_ids",
    )
    base_price = fields.Float(
        string="Combo Price",
        min_display_digits="Product Price",
        compute="_compute_base_price",
        help="The minimum price among the products in this combo. This value will be used to"
        " prorate the price of this combo with respect to the other combos in a combo product."
        " This heuristic ensures that whatever product the user chooses in a combo, it will"
        " always be the same price.",
    )

    @api.constrains("combo_item_ids")
    def _check_combo_item_ids_not_empty(self):
        if any(not combo.combo_item_ids for combo in self):
            raise ValidationError(_("A combo choice must contain at least 1 product."))

    @api.constrains("combo_item_ids")
    def _check_combo_item_ids_no_duplicates(self):
        for combo in self:
            if len(combo.combo_item_ids.mapped("product_id")) < len(
                combo.combo_item_ids
            ):
                raise ValidationError(
                    _("A combo choice can't contain duplicate products.")
                )

    @api.constrains("company_id")
    def _check_company_id(self):
        templates = (
            self.env["product.template"].sudo().search([("combo_ids", "in", self.ids)])
        )
        templates._check_company(fnames=["combo_ids"])
        self.combo_item_ids._check_company(fnames=["product_id"])

    @api.depends("combo_item_ids")
    def _compute_count_combo_item_ids(self):
        self.count_combo_item_ids = 0
        for combo, item_count in self.env["product.combo.item"]._read_group(
            domain=[("combo_id", "in", self.ids)],
            groupby=["combo_id"],
            aggregates=["__count"],
        ):
            combo.count_combo_item_ids = item_count

    @api.depends("company_id")
    def _compute_currency_id(self):
        main_company = self.env["res.company"]._get_main_company()
        for combo in self:
            combo.currency_id = (
                combo.company_id.sudo().currency_id or main_company.currency_id
            )

    @api.depends("combo_item_ids.lst_price", "currency_id")
    def _compute_base_price(self):
        for combo in self:
            prices = [
                item.currency_id._convert(
                    from_amount=item.lst_price,
                    to_currency=combo.currency_id,
                    company=combo.company_id or self.env.company,
                    date=self.env.cr.now(),
                )
                for item in combo.combo_item_ids
            ]
            combo.base_price = min(prices) if prices else 0

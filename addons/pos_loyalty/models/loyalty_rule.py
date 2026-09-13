from odoo import api, fields, models
from odoo.fields import Domain


class LoyaltyRule(models.Model):
    _name = "loyalty.rule"
    _inherit = ["loyalty.rule", "mixin.pos.load"]

    valid_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="Valid Products",
        help="These are the products that are valid for this rule.",
        compute="_compute_valid_products",
    )
    any_product = fields.Boolean(
        help="Technical field, whether all product match",
        compute="_compute_valid_products",
    )

    promo_barcode = fields.Char(
        string="Barcode",
        help="A technical field used as an alternative to the promo code. "
        "This is automatically generated when the promo code is changed.",
        compute="_compute_promo_barcode",
        store=True,
        readonly=False,
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [("program_id", "in", config._get_program_ids().ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "program_id",
            "valid_product_ids",
            "any_product",
            "currency_id",
            "reward_point_amount",
            "reward_point_split",
            "reward_point_mode",
            "minimum_qty",
            "minimum_amount",
            "minimum_amount_tax_mode",
            "mode",
            "code",
        ]

    @api.depends(
        "product_ids", "product_category_id", "product_tag_id", "product_domain"
    )  # TODO later: product tags
    def _compute_valid_products(self):
        for key, rules in self.grouped(
            lambda rule: (
                tuple(rule.product_ids.ids),
                rule.product_category_id.id,
                rule.product_tag_id.id,
                ""
                if rule.product_domain in ("[]", "[['sale_ok', '=', True]]")
                else rule.product_domain,
            )
        ).items():
            if any(key):
                domain = Domain.AND(
                    [
                        [("available_in_pos", "=", True)],
                        rules[:1]._get_domain_valid_product(),
                    ]
                )
                rules.valid_product_ids = self.env["product.product"].search(  # noqa: E8507 - one query per distinct product domain; rules sharing one were merged above
                    domain, order="id"
                )
                rules.any_product = False
            else:
                rules.valid_product_ids = self.env["product.product"]
                rules.any_product = True

    @api.depends("code")
    def _compute_promo_barcode(self):
        for rule in self:
            rule.promo_barcode = self.env["loyalty.card"]._prepare_code()

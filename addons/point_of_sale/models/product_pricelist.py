from odoo import api, models
from odoo.fields import Domain


class ProductPricelist(models.Model):
    _name = "product.pricelist"
    _inherit = ["product.pricelist", "mixin.pos.load"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        pricelist_ids = [preset["pricelist_id"] for preset in data["pos.preset"]]
        return [("id", "in", config._get_available_pricelists().ids + pricelist_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "name", "display_name", "item_ids"]


class ProductPricelistItem(models.Model):
    _name = "product.pricelist.item"
    _inherit = ["product.pricelist.item", "mixin.pos.load"]

    @api.model
    def _load_pos_data_domain(self, data, config):
        template_domain = self.env["product.template"]._load_pos_data_domain(
            data, config
        )
        template_domain = Domain.OR(
            [
                template_domain,
                [("id", "in", [row["id"] for row in data.get("product.template", [])])],
            ]
        )
        pricelist_ids = [p["id"] for p in data["product.pricelist"]]
        return (
            Domain("pricelist_id", "in", pricelist_ids)
            & (
                Domain("product_tmpl_id", "=", False)
                | Domain("product_tmpl_id", "any", template_domain)
            )
            & (
                Domain("product_id", "=", False)
                | Domain("product_id.product_tmpl_id", "any", template_domain)
            )
        )

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "product_tmpl_id",
            "product_id",
            "pricelist_id",
            "price_surcharge",
            "price_discount",
            "price_round",
            "price_min_margin",
            "price_max_margin",
            "company_id",
            "currency_id",
            "date_start",
            "date_end",
            "compute_price",
            "fixed_price",
            "percent_price",
            "base_pricelist_id",
            "base",
            "categ_id",
            "min_quantity",
        ]

from odoo import fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_round

_debug = DebugLog(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_product_accounts(self, fiscal_pos=None):
        accounts = super()._get_product_accounts(fiscal_pos=fiscal_pos)
        if self.categ_id:
            production_account = self.categ_id.property_stock_account_production_cost_id
        else:
            ProductCategory = self.env["product.category"]
            production_account = (
                self.valuation == "real_time"
                and ProductCategory._fields[
                    "property_stock_account_production_cost_id"
                ].get_company_dependent_fallback(ProductCategory)
            ) or self.env["account.account"]
        accounts.update(
            self._map_product_accounts({"production": production_account}, fiscal_pos)
        )
        return accounts

    def action_bom_cost(self):
        templates = self.filtered(
            lambda t: t.product_variant_count == 1 and t.bom_count > 0
        )
        if templates:
            templates.mapped("product_variant_id").action_bom_cost()

    def button_bom_cost(self):
        templates = self.filtered(
            lambda t: t.product_variant_count == 1 and t.bom_count > 0
        )
        if templates:
            templates.mapped("product_variant_id").button_bom_cost()


class ProductProduct(models.Model):
    _inherit = "product.product"

    def button_bom_cost(self):
        self.check_singleton()
        self.with_context(action_button_product=self)._update_standard_price_from_bom()

    def action_bom_cost(self):
        boms_to_recompute = self.env["mrp.bom"].search(
            [
                "|",
                ("product_id", "in", self.ids),
                "&",
                ("product_id", "=", False),
                ("product_tmpl_id", "in", self.mapped("product_tmpl_id").ids),
            ]
        )
        for product in self:
            product.with_context(
                action_button_product=product
            )._update_standard_price_from_bom(boms_to_recompute)

    def _update_standard_price_from_bom(self, boms_to_recompute=False):
        self.check_singleton()
        bom = self.env["mrp.bom"]._get_bom_by_product(self)[self]
        if bom:
            self.standard_price = self._get_bom_price(
                bom, boms_to_recompute=boms_to_recompute
            )
        else:
            bom = self.env["mrp.bom"].search(
                [("byproduct_ids.product_id", "=", self.id)],
                order="sequence, product_id, id",
                limit=1,
            )
            if bom:
                price = self._get_bom_price(
                    bom, boms_to_recompute=boms_to_recompute, byproduct_bom=True
                )
                if price:
                    self.standard_price = price

    def _get_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        self.check_singleton()
        if not bom:
            _debug.logic("bom_price", product=self.id, by="no_bom")
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []
        total = 0
        for opt in bom.operation_ids:
            if opt._is_bom_line_skipped(self):
                continue

            total += opt.cost

        for line in bom.bom_line_ids:
            if line._is_bom_line_skipped(self):
                continue

            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._get_bom_price(
                    line.child_bom_id, boms_to_recompute=boms_to_recompute
                )
                total += (
                    line.product_id.uom_id._get_price_in_unit(
                        child_total, line.product_uom_id
                    )
                    * line.product_qty
                )
            else:
                total += (
                    line.product_id.uom_id._get_price_in_unit(
                        line.product_id.standard_price, line.product_uom_id
                    )
                    * line.product_qty
                )
        if byproduct_bom:
            byproduct_lines = bom.byproduct_ids.filtered(
                lambda b: b.product_id == self and b.cost_share != 0
            )
            product_uom_qty = 0
            for line in byproduct_lines:
                product_uom_qty += line.product_uom_id._get_quantity_in_unit(
                    line.product_qty, self.uom_id, round=False
                )
            byproduct_cost_share = sum(byproduct_lines.mapped("cost_share"))
            _debug.logic(
                "bom_price",
                product=self.id,
                bom=bom.id,
                by="byproduct_share",
                total=total,
                share=byproduct_cost_share,
            )
            if byproduct_cost_share and product_uom_qty:
                return total * byproduct_cost_share / 100 / product_uom_qty
        else:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped("cost_share"))
            if byproduct_cost_share:
                total *= float_round(
                    1 - byproduct_cost_share / 100, precision_rounding=0.0001
                )
            _debug.logic(
                "bom_price",
                product=self.id,
                bom=bom.id,
                by="rolled_up",
                total=total,
                byproduct_share=byproduct_cost_share,
            )
            return bom.product_uom_id._get_price_in_unit(
                total / bom.product_qty, self.uom_id
            )
        return 0.0

    def _compute_value(self):
        non_kit_products = self.filtered(lambda product: not product.is_kit)
        super(ProductProduct, non_kit_products)._compute_value()
        kit_products = self - non_kit_products
        kit_products.company_currency_id = self.env.company.currency_id
        kit_products.total_value = 0.0
        kit_products.avg_cost = 0.0


class ProductCategory(models.Model):
    _inherit = "product.category"

    property_stock_account_production_cost_id = fields.Many2one(
        comodel_name="account.account",
        string="Production Account",
        company_dependent=True,
        ondelete="restrict",
        check_company=True,
        help="""This account will be used as a valuation counterpart for both components and final products for manufacturing orders.
                If there are any workcenter/employee costs, this value will remain on the account once the production is completed.""",
    )

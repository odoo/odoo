from odoo import api, fields, models

from ..tools import debug_log as dbg


class StockRulesReport(models.TransientModel):
    _name = "stock.rules.report"
    _description = "Stock Rules report"

    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        required=True,
    )
    warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        string="Warehouses",
        required=True,
        help="Show the routes that apply on selected warehouses.",
    )
    product_has_variants = fields.Boolean(
        string="Has variants",
        default=False,
        required=True,
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_tmpl_id = self.env["product.template"]
        if "product_id" in fields:
            if self.env.context.get("default_product_id"):
                product_id = self.env["product.product"].browse(
                    self.env.context["default_product_id"]
                )
                product_tmpl_id = product_id.product_tmpl_id
                res["product_tmpl_id"] = product_id.product_tmpl_id.id
                res["product_id"] = product_id.id
            elif self.env.context.get("default_product_tmpl_id"):
                product_tmpl_id = self.env["product.template"].browse(
                    self.env.context["default_product_tmpl_id"]
                )
                res["product_tmpl_id"] = product_tmpl_id.id
                res["product_id"] = product_tmpl_id.product_variant_id.id
                if len(product_tmpl_id.product_variant_ids) > 1:
                    res["product_has_variants"] = True
        if "warehouse_ids" in fields:
            company = product_tmpl_id.company_id or self.env.company
            warehouse_id = (
                self.env["stock.warehouse"]
                .search(
                    self.env["stock.warehouse"]._check_company_domain(company), limit=1
                )
                .id
            )
            if not warehouse_id:
                self.env["stock.warehouse"]._raise_missing_warehouse()
            res["warehouse_ids"] = [(6, 0, [warehouse_id])]
        return res

    def _prepare_report_data(self):
        return {
            "product_id": self.product_id.id,
            "warehouse_ids": self.warehouse_ids.ids,
        }

    def action_print_rules_report(self):
        self.check_singleton()
        data = self._prepare_report_data()
        dbg.pipeline.debug("stock rules report requested: %s", data)
        return self.env.ref("stock.action_report_stock_rule").report_action(
            None, data=data
        )

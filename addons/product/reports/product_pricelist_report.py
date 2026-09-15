import math

from odoo import _, api, models
from odoo.exceptions import UserError


class ReportProductReport_Pricelist(models.AbstractModel):
    _name = "report.product.report_pricelist"
    _description = "Pricelist Report"

    MAX_QUANTITIES = 100
    MAX_PRODUCTS = 1000
    MAX_PRICE_COMPUTATIONS = 5000

    def _get_report_values(self, docids, data):
        return self._prepare_pricelist_rendering_context(data, "pdf")

    @api.readonly
    @api.model
    def get_html(self, data):
        render_values = self._prepare_pricelist_rendering_context(data, "html")
        return self.env["ir.qweb"]._render(
            "product.report_pricelist_page", render_values
        )

    def _prepare_pricelist_rendering_context(self, data, report_type="html"):
        quantities = self._parse_quantities(data.get("quantities"))
        try:
            data_pricelist_id = data.get("pricelist_id")
            pricelist_id = data_pricelist_id and int(data_pricelist_id)
        except ValueError, TypeError:
            pricelist_id = False
        pricelist = self.env["product.pricelist"].browse(pricelist_id).exists()
        if not pricelist:
            pricelist = self.env["product.pricelist"].search([], limit=1)

        active_model = data.get("active_model", "product.template")
        if active_model not in ("product.template", "product.product"):
            raise UserError(_("The pricelist report can only be printed for products."))
        try:
            active_ids = [int(id_) for id_ in data.get("active_ids") or []]
        except ValueError, TypeError:
            raise UserError(_("Invalid product ids.")) from None
        if len(active_ids) > self.MAX_PRODUCTS:
            raise UserError(
                _(
                    "At most %s products can be printed on the pricelist report.",
                    self.MAX_PRODUCTS,
                )
            )
        is_product_tmpl = active_model == "product.template"
        ProductClass = self.env[active_model]

        products = (
            ProductClass.browse(active_ids).exists() if active_ids else ProductClass
        )
        products_data = self._get_products_data(
            is_product_tmpl, products, pricelist, quantities
        )

        return {
            "is_html_type": report_type == "html",
            "is_product_tmpl": is_product_tmpl,
            "display_pricelist_title": data.get("display_pricelist_title", False)
            and bool(data["display_pricelist_title"]),
            "pricelist": pricelist,
            "products": products_data,
            "quantities": quantities,
            "docs": pricelist,
        }

    def _parse_quantities(self, quantities):
        if not quantities:
            return [1]
        try:
            parsed = []
            for qty in quantities:
                value = float(qty)
                if not math.isfinite(value):
                    raise ValueError
                parsed.append(int(value) if value.is_integer() else value)
            quantities = parsed
        except ValueError, TypeError:
            raise UserError(_("Invalid quantities.")) from None
        if len(quantities) > self.MAX_QUANTITIES:
            raise UserError(
                _(
                    "At most %s quantity columns can be printed on the pricelist"
                    " report.",
                    self.MAX_QUANTITIES,
                )
            )
        if any(qty <= 0 for qty in quantities):
            raise UserError(_("Quantities must be positive."))
        return quantities

    def _get_products_data(self, is_product_tmpl, products, pricelist, quantities):
        if not products:
            return []

        if len(products) * len(quantities) > self.MAX_PRICE_COMPUTATIONS:
            raise UserError(
                _(
                    "Too many products and quantity columns requested together."
                    " Reduce either to print this report."
                )
            )

        variants_by_tmpl = {}
        if is_product_tmpl:
            for product in products:
                if product.product_variant_count > 1:
                    variants_by_tmpl[product.id] = product.product_variant_ids
        all_variants = self.env["product.product"].union(*variants_by_tmpl.values())

        prices_by_qty = {}
        variant_prices_by_qty = {}
        for qty in quantities:
            prices_by_qty[qty] = pricelist._get_products_price(products, qty)
            if all_variants:
                variant_prices_by_qty[qty] = pricelist._get_products_price(
                    all_variants, qty
                )

        def prepare_product_payload(product, prices, tmpl_row):
            return {
                "id": product.id,
                "name": (tmpl_row and product.name) or product.display_name,
                "price": {qty: prices[qty].get(product.id, 0.0) for qty in quantities},
                "uom": product.uom_id.name,
            }

        products_data = []
        for product in products:
            data = prepare_product_payload(product, prices_by_qty, is_product_tmpl)
            variants = variants_by_tmpl.get(product.id)
            if variants:
                data["variants"] = [
                    prepare_product_payload(variant, variant_prices_by_qty, False)
                    for variant in variants
                ]
            products_data.append(data)
        return products_data

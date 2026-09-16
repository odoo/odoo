import collections
from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import DOMAIN_PREDICATES

from odoo.addons.stock.const import QUANTITY_FIELDS

_debug = DebugLog(__name__)


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "mixin.mrp.product"]

    _mrp_product_field = "product_id"
    _mrp_bom_field = "variant_bom_ids"

    variant_bom_ids = fields.One2many(
        comodel_name="mrp.bom",
        inverse_name="product_id",
        string="BOM Product Variants",
    )
    bom_line_ids = fields.One2many(
        comodel_name="mrp.bom.line",
        inverse_name="product_id",
        string="BoM Components",
    )

    product_catalog_product_is_in_bom = fields.Boolean(
        compute="_compute_product_is_in_bom_and_mo",
        search="_search_product_catalog_product_is_in_bom",
    )

    product_catalog_product_is_in_mo = fields.Boolean(
        compute="_compute_product_is_in_bom_and_mo",
        search="_search_product_catalog_product_is_in_mo",
    )

    def _get_mrp_variants(self):
        return self

    @api.depends("product_tmpl_id")
    def _compute_bom_count(self):
        bom_ids_by_product = collections.defaultdict(set)
        bom_ids_by_template = collections.defaultdict(set)
        Bom = self.env["mrp.bom"]
        for product, bom_ids in Bom._read_group(
            [("product_id", "in", self.ids)], ["product_id"], ["id:array_agg"]
        ):
            bom_ids_by_product[product.id].update(bom_ids)
        for template, bom_ids in Bom._read_group(
            [
                ("product_id", "=", False),
                ("product_tmpl_id", "in", self.product_tmpl_id.ids),
            ],
            ["product_tmpl_id"],
            ["id:array_agg"],
        ):
            bom_ids_by_template[template.id].update(bom_ids)
        for product, bom_ids in self.env["mrp.bom.byproduct"]._read_group(
            [("product_id", "in", self.ids)], ["product_id"], ["bom_id:array_agg"]
        ):
            bom_ids_by_product[product.id].update(bom_ids)
        for product in self:
            product.bom_count = len(
                bom_ids_by_product[product.id]
                | bom_ids_by_template[product.product_tmpl_id.id]
            )

    @api.depends_context("company")
    def _compute_is_kit(self):
        Bom = self.env["mrp.bom"].sudo()
        domain = Bom._get_domain_kit() & (
            Domain("product_id", "in", self.ids)
            | (
                Domain("product_id", "=", False)
                & Domain("product_tmpl_id", "in", self.product_tmpl_id.ids)
            )
        )
        kit_product_ids = set()
        kit_template_ids = set()
        for product, template in Bom._read_group(
            domain, ["product_id", "product_tmpl_id"]
        ):
            if product:
                kit_product_ids.add(product.id)
            else:
                kit_template_ids.add(template.id)
        _debug.perf.count(
            "is_kit_computed",
            products=self,
            kit_products=len(kit_product_ids),
            kit_templates=len(kit_template_ids),
        )
        for product in self:
            product.is_kit = (
                product.id in kit_product_ids
                or product.product_tmpl_id.id in kit_template_ids
            )

    def _search_is_kit(self, operator, value):
        if operator != "in" or set(value) != {True}:
            return NotImplemented
        Bom = self.env["mrp.bom"].sudo()
        kit_domain = Bom._get_domain_kit()
        bom_tmpl_query = Bom._search(kit_domain & Domain("product_id", "=", False))
        bom_product_query = Bom._search(kit_domain & Domain("product_id", "!=", False))
        return [
            "|",
            ("product_tmpl_id", "in", bom_tmpl_query.subselect("product_tmpl_id")),
            ("id", "in", bom_product_query.subselect("product_id")),
        ]

    def action_archive(self):
        still_used = self._get_still_used_bom_lines()
        _debug.logic("product_archive", products=self, still_used=len(still_used))
        res = super().action_archive()
        return still_used._prepare_action_still_used_warning() or res

    @api.depends_context("order_id")
    def _compute_product_is_in_bom_and_mo(self):
        self.product_catalog_product_is_in_bom = False
        self.product_catalog_product_is_in_mo = False

    def _search_product_catalog_product_is_in_bom(self, operator, value):
        if operator != "in" or set(value) != {True}:
            return NotImplemented
        bom = self.env["mrp.bom"].browse(self.env.context.get("order_id"))
        return [("id", "in", bom.bom_line_ids.product_id.ids)]

    def _search_product_catalog_product_is_in_mo(self, operator, value):
        if operator != "in" or set(value) != {True}:
            return NotImplemented
        production = (
            self.env["mrp.production"].browse(self.env.context.get("order_id")).exists()
        )
        return [("id", "in", production.move_raw_ids.product_id.ids)]

    def _get_total_routes_by_product(self):
        result = super()._get_total_routes_by_product()
        manufacture_routes = (
            self.env["stock.rule"].search([("action", "=", "manufacture")]).route_id
        )
        if not manufacture_routes:
            return result
        boms = {}
        for company, products in self.grouped("company_id").items():
            boms.update(
                self.env["mrp.bom"]._get_bom_by_product(
                    products,
                    bom_type="normal",
                    company_id=(company or self.env.company).id,
                )
            )
        for product in self:
            if boms.get(product):
                result[product.id] |= manufacture_routes
        return result

    def _get_components(self):
        self.check_singleton()
        bom_kit = self.env["mrp.bom"]._get_bom_by_product(
            self, bom_type="phantom", company_id=self.env.company.id
        )[self]
        if not bom_kit:
            return super()._get_components()
        __, bom_sub_lines = bom_kit._explode(self, 1)
        return self.browse().union(
            *(
                bom_line.product_id
                for bom_line, __ in bom_sub_lines
                if bom_line.product_id.is_storable
            )
        )

    @api.depends("uom_id")
    def _compute_mrp_product_qty(self):
        date_from = fields.Datetime.to_string(
            fields.Datetime.now() - timedelta(days=365)
        )
        domain = [
            ("production_id.state", "=", "done"),
            ("product_id", "in", self.ids),
            ("production_id.date_start", ">", date_from),
            ("state", "!=", "cancel"),
            ("picked", "=", True),
        ]
        read_group_res = self.env["stock.move"]._read_group(
            domain, ["product_id", "product_uom_id"], ["quantity:sum"]
        )
        mapped_data = collections.defaultdict(float)
        for product, uom, qty in read_group_res:
            if uom != product.uom_id:
                qty = uom._get_quantity_estimate(qty, product.uom_id)
            mapped_data[product.id] += qty
        for product in self:
            product.mrp_product_qty = product.uom_id.round(
                mapped_data.get(product.id, 0)
            )

    def _prepare_quantities_vals(self, filters, location_domains=None):
        bom_kits = (
            self.env["mrp.bom"]
            .sudo()
            ._get_bom_by_product(
                self, bom_type="phantom", company_id=self.env.company.id
            )
        )
        kits = self.filtered(bom_kits.get)
        regular_products = self - kits
        res = (
            super(ProductProduct, regular_products)._prepare_quantities_vals(
                filters, location_domains=location_domains
            )
            if regular_products
            else {}
        )
        if not kits:
            return res
        qties = self.env.context.get("mrp_compute_quantities", {})
        qties.update(res)
        exploded = {
            product: bom_kits[product]._explode(product, 1)[1] for product in kits
        }
        components = self.browse(
            {
                bom_line.product_id.id
                for bom_sub_lines in exploded.values()
                for bom_line, __ in bom_sub_lines
            }
            - set(qties)
        )
        if components:
            qties.update(
                components.with_env(self.env)
                .with_context(mrp_compute_quantities=qties)
                ._prepare_quantities_vals(filters, location_domains=location_domains)
            )
        for product in kits:
            res[product.id] = product._prepare_kit_quantities_vals(
                bom_kits[product], exploded[product], qties
            )
        return res

    def _prepare_kit_quantities_vals(self, bom_kit, bom_sub_lines, qties):
        self.check_singleton()
        lines_by_component = collections.defaultdict(list)
        for bom_line, bom_line_data in bom_sub_lines:
            lines_by_component[bom_line.product_id].append((bom_line, bom_line_data))
        ratios = collections.defaultdict(list)
        for component, component_lines in lines_by_component.items():
            component = component.with_env(self.env)
            qty_per_bom = 0
            for bom_line, bom_line_data in component_lines:
                if not component.is_storable or bom_line.product_uom_id.is_zero(
                    bom_line_data["qty"]
                ):
                    continue
                qty_per_bom += bom_line.product_uom_id._get_quantity_estimate(
                    bom_line_data["qty"] / bom_line_data["original_qty"],
                    bom_line.product_id.uom_id,
                    round=False,
                )
            if not qty_per_bom:
                continue
            component_vals = qties[component.id]
            for field in QUANTITY_FIELDS:
                ratios[field].append(component_vals[field] / qty_per_bom)
        if not ratios:
            _debug.logic(
                "kit_quantities",
                product=self.id,
                bom=bom_kit.id,
                by="no_storable_component",
            )
            return dict.fromkeys(QUANTITY_FIELDS, 0)
        _debug.logic(
            "kit_quantities",
            product=self.id,
            bom=bom_kit.id,
            by="min_ratio",
            components=len(lines_by_component),
        )
        return {
            field: self.uom_id.round(
                min(values) * bom_kit.product_qty, rounding_method="DOWN"
            )
            // 1
            for field, values in ratios.items()
        }

    def action_view_bom(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.product_open_bom"
        )
        template_ids = self.product_tmpl_id.ids
        action["context"] = {
            "default_product_tmpl_id": template_ids[0] if template_ids else False,
            "default_product_id": (
                self.ids[0]
                if self.ids and self.env.user.has_group("product.group_product_variant")
                else False
            ),
        }
        action["domain"] = [
            "|",
            "|",
            ("byproduct_ids.product_id", "in", self.ids),
            ("product_id", "in", self.ids),
            "&",
            ("product_id", "=", False),
            ("product_tmpl_id", "in", template_ids),
        ]
        return action

    def action_view_quants(self):
        bom_kits = self.env["mrp.bom"]._get_bom_by_product(
            self, bom_type="phantom", company_id=self.env.company.id
        )
        components = self - self.browse().union(*bom_kits)
        for product, bom_kit in bom_kits.items():
            __, bom_sub_lines = bom_kit._explode(product, 1)
            components |= self.browse().union(
                *(bom_line.product_id for bom_line, __ in bom_sub_lines)
            )
        res = super(ProductProduct, components).action_view_quants()
        if bom_kits:
            res["context"].pop("default_product_tmpl_id", None)
        return res

    def _has_all_variant_values(self, product_template_attribute_value_ids):
        self.check_singleton()
        return len(
            self.product_template_attribute_value_ids
            & product_template_attribute_value_ids
        ) == len(product_template_attribute_value_ids.attribute_id)

    def _get_phantom_bom_products(self):
        return self.search([("is_kit", "=", True)])

    def _get_quantity_search_candidates(self, location_domains=None):
        return (
            super()._get_quantity_search_candidates(location_domains=location_domains)
            | self._get_phantom_bom_products()
        )

    def _get_product_ids_from_quants(self, operator, value, filters=None):
        op = DOMAIN_PREDICATES.get(operator)
        if not op:
            return NotImplemented
        product_ids = super()._get_product_ids_from_quants(operator, value, filters)
        if product_ids is NotImplemented:
            return NotImplemented
        kits = self._get_phantom_bom_products()
        if not kits:
            return product_ids
        matching, not_matching = set(), set()
        for product, qty_available in zip(
            kits, kits.mapped("qty_available"), strict=True
        ):
            (matching if op(qty_available, value) else not_matching).add(product.id)
        return sorted((set(product_ids) - not_matching) | matching)

    def _update_uom(self, to_uom_id):
        for model, product_field, domain, context in (
            (
                "mrp.bom",
                "product_tmpl_id",
                [("product_tmpl_id", "in", self.product_tmpl_id.ids)],
                None,
            ),
            (
                "mrp.bom.line",
                "product_id",
                [("product_id", "in", self.ids)],
                {"mail_notrack": True},
            ),
            (
                "mrp.bom.byproduct",
                "product_id",
                [("product_id", "in", self.ids)],
                {"mail_notrack": True},
            ),
            ("mrp.production", "product_id", [("product_id", "in", self.ids)], None),
            ("mrp.unbuild", "product_id", [("product_id", "in", self.ids)], None),
        ):
            self._restamp_uom(
                model,
                to_uom_id,
                domain=domain,
                product_field=product_field,
                context=context,
            )
        return super()._update_uom(to_uom_id)

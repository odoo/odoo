import collections

from odoo import api, fields, models
from odoo.fields import Domain


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "mixin.mrp.product"]

    _mrp_product_field = "product_tmpl_id"
    _mrp_bom_field = "bom_ids"

    bom_line_ids = fields.One2many(
        comodel_name="mrp.bom.line",
        inverse_name="product_tmpl_id",
        string="BoM Components",
    )
    bom_ids = fields.One2many(
        comodel_name="mrp.bom",
        inverse_name="product_tmpl_id",
        string="Bill of Materials",
    )

    def _get_mrp_variants(self):
        return self.product_variant_ids

    def _compute_bom_count(self):
        bom_ids_by_template = collections.defaultdict(set)
        for template, bom_ids in self.env["mrp.bom"]._read_group(
            [("product_tmpl_id", "in", self.ids)],
            ["product_tmpl_id"],
            ["id:array_agg"],
        ):
            bom_ids_by_template[template.id].update(bom_ids)
        for product, bom_ids in self.env["mrp.bom.byproduct"]._read_group(
            [("product_id.product_tmpl_id", "in", self.ids)],
            ["product_id"],
            ["bom_id:array_agg"],
        ):
            bom_ids_by_template[product.product_tmpl_id.id].update(bom_ids)
        for product in self:
            product.bom_count = len(bom_ids_by_template.get(product.id, ()))

    @api.depends_context("company")
    def _compute_is_kit(self):
        Bom = self.env["mrp.bom"].sudo()
        kit_template_ids = {
            template.id
            for [template] in Bom._read_group(
                Bom._get_domain_kit() & Domain("product_tmpl_id", "in", self.ids),
                ["product_tmpl_id"],
            )
        }
        for template in self:
            template.is_kit = template.id in kit_template_ids

    def _search_is_kit(self, operator, value):
        if operator != "in" or set(value) != {True}:
            return NotImplemented
        Bom = self.env["mrp.bom"].sudo()
        bom_query = Bom._search(Bom._get_domain_kit())
        return [("id", "in", bom_query.subselect("product_tmpl_id"))]

    def action_archive(self):
        still_used = self._get_still_used_bom_lines()
        res = super().action_archive()
        return still_used._prepare_action_still_used_warning() or res

    def _compute_show_qty_status_button(self):
        super()._compute_show_qty_status_button()
        for template in self:
            if template.is_kit:
                template.show_on_hand_qty_status_button = (
                    template.product_variant_count <= 1
                )
                template.show_forecasted_qty_status_button = False

    def _is_product_quants_open_required(self):
        return super()._is_product_quants_open_required() or self.is_kit

    @api.depends("product_variant_ids.mrp_product_qty", "uom_id")
    def _compute_mrp_product_qty(self):
        for template in self:
            template.mrp_product_qty = template.uom_id.round(
                sum(template.product_variant_ids.mapped("mrp_product_qty"))
            )

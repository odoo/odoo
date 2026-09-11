# Copyright (C) 2014-Today GRAP (http://www.grap.coop)
# Copyright (C) 2016-Today La Louve (http://www.lalouve.net)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Related to display product product information if is_product_variant
    barcode_rule_id = fields.Many2one(
        string="Barcode Rule",
        compute="_compute_barcode_rule_id",
        inverse="_inverse_barcode_rule_id",
        comodel_name="barcode.rule",
    )

    barcode_base = fields.Integer(
        compute="_compute_barcode_base",
        inverse="_inverse_barcode_base",
    )

    generate_type = fields.Selection(
        string="Generate Type",
        related="product_variant_ids.barcode_rule_id.generate_type",
        readonly=True,
    )

    # Compute Section
    @api.depends("product_variant_ids.barcode_rule_id")
    def _compute_barcode_rule_id(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        )
        for template in unique_variants:
            template.barcode_rule_id = template.product_variant_ids.barcode_rule_id
        for template in self - unique_variants:
            template.barcode_rule_id = False

    def _inverse_barcode_rule_id(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.barcode_rule_id = template.barcode_rule_id

    @api.depends("product_variant_ids.barcode_base")
    def _compute_barcode_base(self):
        unique_variants = self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        )
        for template in unique_variants:
            template.barcode_base = template.product_variant_ids.barcode_base
        for template in self - unique_variants:
            template.barcode_base = False

    def _inverse_barcode_base(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.barcode_base = template.barcode_base

    # View Section
    def generate_base(self):
        self.product_variant_ids.generate_base()

    def generate_barcode(self):
        self.ensure_one()
        self.product_variant_ids.generate_barcode()

    @api.onchange("barcode_rule_id")
    def onchange_barcode_rule_id(self):
        self.generate_type = self.barcode_rule_id.generate_type

    # Overload Section
    def _get_related_fields_variant_template(self):
        res = super()._get_related_fields_variant_template()
        res += ["barcode_rule_id", "barcode_base"]
        return res

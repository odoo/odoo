# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    @api.depends('quant_ids', 'package_type_id')
    def _compute_weight(self):
        if self.env.context.get('picking_id'):
            package_weights = defaultdict(float)
            res_groups = self.env['stock.move.line']._read_group(
                [('result_package_id', 'in', self.ids), ('product_id', '!=', False), ('picking_id', '=', self.env.context['picking_id'])],
                ['result_package_id', 'product_id', 'product_uom_id', 'quantity'],
                ['__count'],
            )
            for result_package, product, product_uom, quantity, count in res_groups:
                package_weights[result_package.id] += (
                    count
                    * product_uom._compute_quantity(quantity, product.uom_id)
                    * product.weight
                )
        for package in self:
            weight = package.package_type_id.base_weight or 0.0
            if self.env.context.get('picking_id'):
                package.weight = weight + package_weights[package.id]
            else:
                for quant in package.quant_ids:
                    weight += quant.quantity * quant.product_id.weight
                package.weight = weight

    def _get_default_weight_uom(self):
        return self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package in self:
            package.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_is_kg(self):
        self.weight_is_kg = False
        uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if uom_id == self.env.ref('uom.product_uom_kgm'):
            self.weight_is_kg = True
        self.weight_uom_rounding = uom_id.rounding

    weight = fields.Float(compute='_compute_weight', digits='Stock Weight', help="Total weight of all the products contained in the package.")
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name', readonly=True, default=_get_default_weight_uom)
    weight_is_kg = fields.Boolean("Technical field indicating whether weight uom is kg or not (i.e. lb)", compute="_compute_weight_is_kg")
    weight_uom_rounding = fields.Float("Technical field indicating weight's number of decimal places", compute="_compute_weight_is_kg")
    shipping_weight = fields.Float(string='Shipping Weight', help="Total weight of the package.")

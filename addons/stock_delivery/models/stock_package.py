# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPackage(models.Model):
    _inherit = "stock.package"

    @api.depends('quant_ids', 'package_type_id')
    def _compute_weight(self):
        packages_weight = self.sudo()._get_weight(self.env.context.get('picking_id'))
        for package in self:
            package.weight = packages_weight[package]

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
    package_carrier_type = fields.Selection(related='package_type_id.package_carrier_type')

    def _pre_put_in_pack_hook(self, package_id=False, package_type_id=False, package_name=False, from_package_wizard=False):
        res = super()._pre_put_in_pack_hook(package_id, package_type_id, package_name, from_package_wizard)
        move_lines = self.move_line_ids
        if res and move_lines.carrier_id:
            if self.env.context.get('picking_id'):
                move_lines = move_lines.filtered(lambda ml: ml.picking_id.id == self.env.context['picking_id'])

            context = res.get('context', {})
            context['default_package_carrier_type'] = move_lines._get_package_carrier_type_for_pack()
            res['context'] = context
        return res

    def _post_put_in_pack_hook(self):
        res = super()._post_put_in_pack_hook()
        weight = self.env.context.get('weight')
        if weight:
            res.shipping_weight = weight
        return res

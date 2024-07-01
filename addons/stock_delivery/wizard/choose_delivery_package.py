# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class ChooseDeliveryPackage(models.TransientModel):
    _name = 'choose.delivery.package'
    _description = 'Delivery Package Selection Wizard'

    move_line_ids = fields.Many2many('stock.move.line')
    delivery_package_type_id = fields.Many2one('stock.package.type', 'Delivery Package Type', check_company=True)
    shipping_weight = fields.Float('Shipping Weight', compute='_compute_shipping_weight', store=True, readonly=False)
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')
    company_id = fields.Many2one(related='move_line_ids.company_id')

    @api.depends('delivery_package_type_id')
    def _compute_weight_uom_name(self):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for package in self:
            package.weight_uom_name = weight_uom_id.name

    @api.depends('delivery_package_type_id')
    def _compute_shipping_weight(self):
        for rec in self:
            move_line_ids = rec.move_line_ids._to_pack()
            # Add package weights to shipping weight, package base weight is defined in package.type
            total_weight = rec.delivery_package_type_id.base_weight or 0.0
            for ml in move_line_ids:
                qty = ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)
                total_weight += qty * ml.product_id.weight
            rec.shipping_weight = total_weight

    @api.onchange('delivery_package_type_id', 'shipping_weight')
    def _onchange_package_type_weight(self):
        if self.delivery_package_type_id.max_weight and self.shipping_weight > self.delivery_package_type_id.max_weight:
            warning_mess = {
                'title': _('Package too heavy!'),
                'message': _('The weight of your package is higher than the maximum weight authorized for this package type. Please choose another package type.')
            }
            return {'warning': warning_mess}

    def action_put_in_pack(self):
        return self.move_line_ids.action_put_in_pack(weight=self.shipping_weight, package_type=self.delivery_package_type_id, from_package_wizard=True)

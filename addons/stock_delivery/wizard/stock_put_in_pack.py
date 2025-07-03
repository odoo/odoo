# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPutInPack(models.TransientModel):
    _inherit = 'stock.put.in.pack'

    shipping_weight = fields.Float('Shipping Weight', compute='_compute_shipping_weight', store=True, readonly=False)
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')
    package_carrier_type = fields.Char('Carrier Type')

    def _compute_weight_uom_name(self):
        self.weight_uom_name = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter().name

    @api.depends('package_type_id', 'result_package_id')
    def _compute_shipping_weight(self):
        for wizard in self:
            if not wizard.package_carrier_type or wizard.package_ids:
                # No need to compute weights for multi-level packages as only lowest-level packages are going to be delivered.
                wizard.shipping_weight = 0
                continue

            move_lines = wizard.move_line_ids
            if wizard.result_package_id:
                # If we use an existing package, we need to factor in the move lines already in the package.
                move_lines += wizard.result_package_id.move_line_ids

            # Add package weights to shipping weight, package base weight is defined in package.type
            total_weight = wizard.package_type_id.base_weight or wizard.result_package_id.package_type_id.base_weight or 0.0
            for ml in move_lines:
                qty = ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)
                total_weight += qty * ml.product_id.weight
            wizard.shipping_weight = total_weight

    @api.onchange('package_type_id', 'result_package_id', 'shipping_weight')
    def _onchange_package_type_weight(self):
        max_weight = self.package_type_id.max_weight if self.package_type_id else self.result_package_id.package_type_id.max_weight
        if self.package_carrier_type and max_weight and self.shipping_weight > max_weight:
            if self.package_type_id:
                message = self.env._('The weight of your package is higher than the maximum weight authorized for this package type. Please choose another package type.')
            else:
                message = self.env._('The weight of your package is higher than the maximum weight authorized for its package type. Please choose another package.')
            return {
                'warning': {
                    'title': self.env._('Package too heavy!'),
                    'message': message,
                }
            }

    def _get_put_in_pack_context(self):
        context = super()._get_put_in_pack_context()
        return {
            **context,
            'weight': self.shipping_weight,
        } if self.package_carrier_type else context

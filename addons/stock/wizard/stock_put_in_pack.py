# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPutInPack(models.TransientModel):
    _name = 'stock.put.in.pack'
    _description = 'Put In Pack Wizard'

    location_dest_id = fields.Many2one('stock.location', 'Destination')
    move_line_ids = fields.Many2many('stock.move.line', string='Move lines')
    package_ids = fields.Many2many('stock.package', string='Packages')
    package_type_id = fields.Many2one('stock.package.type', 'Package Type')
    package_type_sequence_id = fields.Many2one(related="package_type_id.sequence_id")
    result_package_id = fields.Many2one('stock.package', 'Package')
    origin_package_ids = fields.Many2many('stock.package', compute='_compute_origin_package_ids')
    weight = fields.Float('Weight', compute='_compute_weight')

    def _compute_origin_package_ids(self):
        for wizard in self:
            packages = wizard.package_ids
            if wizard.move_line_ids:
                packages |= wizard.move_line_ids.result_package_id
            wizard.origin_package_ids = packages.parent_package_id

    @api.depends('package_type_id', 'result_package_id')
    def _compute_weight(self):
        for wizard in self:
            total_weight = 0.0
            if wizard.move_line_ids:
                for ml in wizard.move_line_ids:
                    qty = ml.uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id)
                    total_weight += qty * ml.product_id.weight
            packages = wizard.result_package_id._origin | wizard.package_ids._origin

            picking_id = self.env.context.get('picking_ids')
            if not picking_id and self.env.context.get('active_model') == 'stock.picking':
                picking_id = self.env.context.get('active_id')
            packages_weight = packages._get_weight(picking_id, include_quants=bool(picking_id))
            for package in packages:
                total_weight += packages_weight.get(package, 0.0)

            wizard.weight = total_weight

    @api.onchange('package_type_id', 'result_package_id', 'weight')
    def _onchange_package_type_weight(self):
       return self._check_package_weight()

    @api.onchange('package_type_id')
    def _onchange_package_type_id(self):
        if self.package_type_id and self.result_package_id and self.result_package_id.package_type_id != self.package_type_id:
            self.result_package_id = False

    def action_put_in_pack(self):
        context = self._get_put_in_pack_context()
        if self.package_ids:
            return self.package_ids.with_context(**context).action_put_in_pack(package_id=self.result_package_id.id, package_type_id=self.package_type_id.id)
        return self.move_line_ids.with_context(**context).action_put_in_pack(package_id=self.result_package_id.id, package_type_id=self.package_type_id.id)

    def _check_package_weight(self):
        package_type = self.package_type_id or self.result_package_id.package_type_id
        max_weight = package_type.max_weight + package_type.base_weight
        weight = self._get_weight_to_check()
        if max_weight and weight > max_weight:
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

    def _get_weight_to_check(self):
        return self.weight

    def _get_put_in_pack_context(self):
        return {
            **self.env.context,
            'from_package_wizard': True,
        }

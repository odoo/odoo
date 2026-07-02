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
    result_package_id = fields.Many2one('stock.package', 'Package', compute='_compute_package_data', store=True, readonly=False)
    origin_package_ids = fields.Many2many('stock.package', compute='_compute_origin_package_ids')
    package_capacity = fields.Float('Package Size', compute='_compute_package_data', store=True, readonly=False)
    move_id = fields.Many2one('stock.move')

    def _compute_origin_package_ids(self):
        for wizard in self:
            packages = wizard.package_ids
            if wizard.move_line_ids:
                packages |= wizard.move_line_ids.result_package_id
            wizard.origin_package_ids = packages.parent_package_id

    @api.depends('package_type_id')
    def _compute_package_data(self):
        if self.package_type_id and self.result_package_id and self.result_package_id.package_type_id != self.package_type_id:
            self.result_package_id = False
        # recalculate package size to match the relative factor
        for wizard in self:
            wizard.package_capacity = None
            if self.env.context.get('show_package_capacity') and wizard.package_type_id:
                # get uom from package type
                uom_id = self.env["uom.uom"].search([('package_type_id', '=', wizard.package_type_id)], limit=1)
                if not uom_id or not self.move_id:
                    continue
                # put size as relative factor
                wizard.package_capacity = uom_id._compute_quantity(1, self.move_id.uom_id, round=False)

    def action_put_in_pack(self):
        context = self._get_put_in_pack_context()
        if self.package_ids:
            return self.package_ids.with_context(**context).action_put_in_pack(package_id=self.result_package_id.id, package_type_id=self.package_type_id.id)
        result = self.move_line_ids.with_context(**context).action_put_in_pack(package_id=self.result_package_id.id, package_type_id=self.package_type_id.id, package_capacity=self.package_capacity)

        # go back to Detailed Operations window, if this wizard
        # was opened from there
        if self.move_id:
            return self.move_id.action_show_details()
        return result

    def _get_put_in_pack_context(self):
        return {
            **self.env.context,
            'from_package_wizard': True,
        }

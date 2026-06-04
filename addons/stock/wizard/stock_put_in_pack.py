# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPutInPack(models.TransientModel):
    _name = 'stock.put.in.pack'
    _description = 'Put In Pack Wizard'

    location_dest_id = fields.Many2one('stock.location', 'Destination')
    move_line_ids = fields.Many2many('stock.move.line', string='Move lines')
    package_ids = fields.Many2many('stock.package', string='Packages')
    package_type_id = fields.Many2one('stock.package.type', 'Package Type', compute='_compute_package_type_id', store=True, readonly=False)
    result_package_id = fields.Many2one('stock.package', 'Package', compute='_compute_result_package_id', store=True, readonly=False)
    origin_package_ids = fields.Many2many('stock.package', compute='_compute_origin_package_ids')
    package_capacity = fields.Float('Package Size', compute='_compute_package_capacity', store=True, readonly=False)
    package_uom = fields.Char('Unit', compute='_compute_package_uom')
    show_package_capacity = fields.Boolean(compute='_compute_show_package_capacity')

    @api.depends('move_line_ids')
    def _compute_package_type_id(self):
        self.package_type_id = None
        for wizard in self:
            if len(wizard.move_line_ids) == 1:
                move_line = wizard.move_line_ids[0]
                wizard.package_type_id = move_line.move_id.packaging_uom_id.package_type_id

    @api.depends('move_line_ids')
    def _compute_package_uom(self):
        self.package_uom = None
        for wizard in self:
            if len(wizard.move_line_ids) == 1:
                move_line = wizard.move_line_ids[0]
                wizard.package_uom = move_line.uom_id.name

    def _compute_origin_package_ids(self):
        for wizard in self:
            packages = wizard.package_ids
            if wizard.move_line_ids:
                packages |= wizard.move_line_ids.result_package_id
            wizard.origin_package_ids = packages.parent_package_id

    @api.depends('package_type_id')
    def _compute_result_package_id(self):
        for wizard in self:
            if wizard.package_type_id and wizard.result_package_id and wizard.result_package_id.package_type_id != wizard.package_type_id:
                wizard.result_package_id = False

    @api.depends('package_type_id', 'show_package_capacity')
    def _compute_package_capacity(self):
        # Recalculate package size to match the relative factor.
        for wizard in self:
            wizard.package_capacity = None

            if wizard.show_package_capacity:
                move_line = wizard.move_line_ids[0]
                # Set capacity as total quantity.
                wizard.package_capacity = move_line.quantity

                # If there is a package type linked to an UoM, set capacity as its relative factor.
                if wizard.package_type_id:
                    # Get the package type's UoM.
                    uom_id = self.env['uom.uom'].search([('package_type_id', '=', wizard.package_type_id.id)], limit=1)
                    if not uom_id or not move_line.uom_id:
                        continue
                    # Set capacity as relative factor.
                    wizard.package_capacity = uom_id._compute_quantity(1, move_line.uom_id, round=False)

    @api.depends('move_line_ids')
    def _compute_show_package_capacity(self):
        for wizard in self:
            wizard.show_package_capacity = len(wizard.move_line_ids) == 1

    def action_put_in_pack(self):
        context = self._get_put_in_pack_context()
        if self.package_ids:
            return self.package_ids.with_context(**context).action_put_in_pack(package_id=self.result_package_id.id, package_type_id=self.package_type_id.id)
        return self.move_line_ids.with_context(**context).action_put_in_pack(
            package_id=self.result_package_id.id,
            package_type_id=self.package_type_id.id,
            package_capacity=self.package_capacity,
        )

    def _get_put_in_pack_context(self):
        return {
            **self.env.context,
            'from_package_wizard': True,
        }

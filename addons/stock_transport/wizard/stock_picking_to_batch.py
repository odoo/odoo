from odoo import fields, models, api


class StockPickingToBatch(models.TransientModel):
    _inherit = 'stock.picking.to.batch'

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    vehicle_category_id = fields.Many2one(
        'fleet.vehicle.model.category', string="Vehicle Category", compute='_compute_vehicle_category_id', readonly=False, store=True)
    dock_id = fields.Many2one('stock.location', string="Dock Location", domain="[('is_a_dock', '=', True)]")

    @api.depends('vehicle_id')
    def _compute_vehicle_category_id(self):
        for rec in self:
            rec.vehicle_category_id = rec.vehicle_id.category_id if rec.vehicle_id else False

    def attach_pickings(self):
        super().attach_pickings()

        pickings = self.env['stock.picking'].browse(self.env.context.get('active_ids'))
        batch = self.env['stock.picking.batch'].search([
            ('picking_ids', 'in', pickings.ids)
        ], limit=1)
        batch.write({
            'dock_id': self.dock_id.id,
            'vehicle_id': self.vehicle_id.id,
            'vehicle_category_id': self.vehicle_category_id.id,
        })

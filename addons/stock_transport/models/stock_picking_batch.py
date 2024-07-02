# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    @api.model
    def _default_end_date(self):
        self.end_date = fields.datetime.now()

    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    vehicle_category_id = fields.Many2one(
        'fleet.vehicle.model.category', string="Vehicle Category", compute='_compute_vehicle_category_id', store=True, readonly=False)
    dock_id = fields.Many2one('stock.location', string="Dock Location", domain="[('is_a_dock', '=', True)]")
    vehicle_details = fields.Char(
        "Vehicle Details", compute='_compute_vehicle_details')
    max_weight = fields.Float(string="Max Weight (Kg)",
                              related='vehicle_category_id.max_weight')
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')
    max_volume = fields.Float(string="Max Volume (m³)",
                              related='vehicle_category_id.max_volume')
    volume_uom_name = fields.Char(string='Volume unit of measure label', compute='_compute_volume_uom_name')
    driver_id = fields.Many2one(
        related="vehicle_id.driver_id", string="Driver")
    used_weight_percentage = fields.Float(
        string="Weight %", compute='_compute_used_weight_percentage', store=True)
    used_volume_percentage = fields.Float(
        string="Volume %", compute='_compute_used_volume_percentage', store=True)
    max_picking_weight = fields.Float(string="Weight", compute='_compute_used_weight_percentage', store=True)
    max_picking_volume = fields.Float(string="Volume", compute='_compute_used_volume_percentage', store=True)
    end_date = fields.Datetime('End Date', default=_default_end_date)
    picking_info = fields.Char(string="Picking Type Information",
                            compute='_compute_picking_info')
    batch_max_pickings = fields.Integer(string="Transfer", related='picking_type_id.batch_max_pickings')
    batch_max_lines = fields.Integer(string="Lines", related='picking_type_id.batch_max_lines')
    batch_properties = fields.Properties(
        'Properties',
        definition='picking_type_id.picking_properties_definition')

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        res._update_sequences()
        return res

    def _update_sequences(self):
        sorted_records = self.picking_ids.sorted(key=lambda r: r.zip_code or '0')
        for idx, record in enumerate(sorted_records):
            record.sequence = idx

    @api.depends('vehicle_id')
    def _compute_vehicle_category_id(self):
        for rec in self:
            rec.vehicle_category_id = rec.vehicle_id.category_id if rec.vehicle_id else False

    @api.depends('vehicle_id', 'max_picking_weight', 'max_picking_volume')
    def _compute_vehicle_details(self):
        for record in self:
            vehicle_details = []
            if record.vehicle_id:
                vehicle_details.append(record.vehicle_id.name)
            vehicle_details.append(f"{round(record.max_picking_weight, 2)} {record.weight_uom_name}") if record.max_picking_weight else vehicle_details.append(f"0 {record.weight_uom_name}")
            vehicle_details.append(f"{round(record.max_picking_volume, 2)} {record.volume_uom_name}") if record.max_picking_volume else vehicle_details.append(f"0 {record.volume_uom_name}")
            record.vehicle_details = ', '.join(vehicle_details)

    def _compute_weight_uom_name(self):
        for category in self:
            category.weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()

    def _compute_volume_uom_name(self):
        for category in self:
            category.volume_uom_name = self.env['product.template']._get_volume_uom_name_from_ir_config_parameter()

    @api.depends('picking_ids.weight', 'vehicle_category_id.max_weight')
    def _compute_used_weight_percentage(self):
        for batch in self:
            batch.max_picking_weight = sum(picking.weight for picking in batch.picking_ids)
            batch_vehicle_max_weight = batch.vehicle_category_id.max_weight
            used_weight_percentage = 100 * (batch.max_picking_weight / batch_vehicle_max_weight) if batch_vehicle_max_weight else 0.0
            batch.used_weight_percentage = used_weight_percentage

    @api.depends('picking_ids.volume', 'vehicle_category_id.max_volume')
    def _compute_used_volume_percentage(self):
        for batch in self:
            batch.max_picking_volume = sum(picking.volume for picking in batch.picking_ids)
            batch_vehicle_max_volume = batch.vehicle_category_id.max_volume
            used_volume_percentage = 100 * (batch.max_picking_volume / batch_vehicle_max_volume) if batch_vehicle_max_volume else 0.0
            batch.used_volume_percentage = used_volume_percentage

    @api.depends('picking_type_id', 'max_picking_weight', 'max_picking_volume')
    def _compute_picking_info(self):
        for record in self:
            picking_type = f"{record.picking_type_id.name}: " if record.picking_type_id else ''
            max_picking_weight = f"{round(record.max_picking_weight, 2)}{record.weight_uom_name}" if record.max_picking_weight else 'f"0 {record.weight_uom_name}"'
            max_picking_volume = f"{round(record.max_picking_volume, 2)}{record.volume_uom_name}" if record.max_picking_volume else 'f"0 {record.volume_uom_name}"'
            picking_info_str = f"{picking_type}{max_picking_weight}, {max_picking_volume}".rstrip(', ')
            record.picking_info = picking_info_str

    @api.depends('dock_id')
    def _compute_move_ids(self):
        super()._compute_move_ids()
        if self.dock_id:
            parent_path_id = [int(parent_id) for parent_id in self.dock_id.parent_path.split('/')[:-1]]
            for line in self.move_line_ids:
                if line.location_dest_id.id in parent_path_id:
                    line.location_dest_id = self.dock_id

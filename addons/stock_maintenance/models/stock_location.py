from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    equipment_count = fields.Integer('Equipment Count', compute='_compute_equipment_count')

    def _compute_equipment_count(self):
        equipment_data = self.env['maintenance.equipment']._read_group([('location_id', 'in', self.ids)], ['location_id'], ['__count'])
        mapped_data = {location.id: count for location, count in equipment_data}
        for location in self:
            location.equipment_count = mapped_data.get(location.id, 0)

    def action_view_equipments_records(self):
        action = self.env["ir.actions.actions"]._for_xml_id("maintenance.hr_equipment_action")
        action['domain'] = [('location_id', '=', self.id)]
        return action

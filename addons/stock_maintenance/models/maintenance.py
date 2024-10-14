# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    match_serial = fields.Boolean(compute='_compute_match_serial')

    @api.depends('serial_no')
    def _compute_match_serial(self):
        matched_serial_data = self.env['stock.lot']._read_group(
            [('name', 'in', self.mapped('serial_no'))],
            ['name'],
            ['__count'],
        )
        matched_serial_count = dict(matched_serial_data)
        for equipment in self:
            equipment.match_serial = matched_serial_count.get(equipment.serial_no, 0)

    def action_open_matched_serial(self):
        self.ensure_one()
        action = self.env.ref('stock.action_production_lot_form', raise_if_not_found=False)
        if not action:
            return True
        action_dict = action._get_action_dict()
        action_dict['context'] = {'search_default_name': self.serial_no}
        return action_dict

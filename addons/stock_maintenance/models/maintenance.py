from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    location_id = fields.Many2one('stock.location', 'Location', domain="[('usage', '=', 'internal')]")
    matching_serials = fields.Many2many('stock.lot', compute='_compute_matching_serials')

    @api.depends('serial_no')
    def _compute_matching_serials(self):
        self.matching_serials = False
        if not (self.env.user.has_group('stock.group_stock_user') and
                self.env.user.has_group('stock.group_production_lot')):
            return
        serials = self.env['stock.lot'].search_fetch([], ['name'])
        for equipment in self:
            equipment.matching_serials = self.env['stock.lot']
            if not equipment.serial_no:
                continue
            # The same equipment can have more than one matching serial numbers
            # and a serial number can be assigned to multiple equipment.
            for serial in serials:
                if equipment.serial_no == serial.name:
                    equipment.matching_serials |= serial

    def action_open_matched_serial(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_production_lot_form')
        if len(self.matching_serials) == 1:
            action.update({
                'views': [(False, 'form')],
                'res_id': self.matching_serials.id,
            })
        else:
            action.update({
                'context': {},
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', self.matching_serials.ids)],
            })
        return action

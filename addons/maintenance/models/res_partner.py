from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    maintenance_equipment_ids = fields.One2many('maintenance.equipment', 'customer_id', 'Maintenance Equipment')
    maintenance_equipment_count = fields.Integer(compute='_compute_maintenance_equipment_count', string='Maintenance Equipment Count')

    def _compute_maintenance_equipment_count(self):
        self.maintenance_equipment_count = len(self.maintenance_equipment_ids)

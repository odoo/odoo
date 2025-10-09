# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    equipment_assign_to = fields.Selection(selection_add=[('vehicle', 'Vehicle')], default='vehicle')
    vehicle_id = fields.Many2one('fleet.vehicle', compute='_compute_equipment_assign_to_date',
        store=True, readonly=False, string="Vehicle", index='btree_not_null', tracking=True)
    is_assigned = fields.Boolean(compute='_compute_is_assigned', search='_search_is_assigned')

    @api.depends(lambda self: self._get_assign_fields() + ['equipment_assign_to'])
    def _compute_owner(self):
        fleet_equipments = self.filtered(lambda e: e.equipment_assign_to in ('vehicle', 'other'))
        other_equipments = self - fleet_equipments
        if other_equipments:
            super(MaintenanceEquipment, other_equipments)._compute_owner()
        for equipment in fleet_equipments:
            if equipment.equipment_assign_to == 'vehicle':
                equipment.owner_user_id = equipment.vehicle_id.manager_id.user_id.id or self.env.user.id
            else:
                equipment.owner_user_id = self.env.user.id

    @api.depends('equipment_assign_to')
    def _compute_equipment_assign_to_date(self):
        fleet_equipments = self.filtered(lambda e: e.equipment_assign_to in ('vehicle', 'other'))
        other_equipments = self - fleet_equipments
        if other_equipments:
            super(MaintenanceEquipment, other_equipments)._compute_equipment_assign_to_date()
        assign_fields = self._get_assign_fields()
        for equipment in fleet_equipments:
            values = dict.fromkeys(assign_fields, False)
            if equipment.equipment_assign_to == 'vehicle':
                values['vehicle_id'] = equipment.vehicle_id
            else:
                values = {field: equipment[field] or False for field in assign_fields}
            values['assign_date'] = fields.Date.context_today(self)
            equipment.update(values)

    @api.depends(lambda self: self._get_assign_fields())
    def _compute_is_assigned(self):
        assign_fields = self._get_assign_fields()
        for equipment in self:
            equipment.is_assigned = any(equipment[field] for field in assign_fields)

    def _get_assign_fields(self):
        return super()._get_assign_fields() + ['vehicle_id']

    def _search_is_assigned(self, operator, value):
        if operator not in ('=', '!=') or value not in (True, False):
            return NotImplemented

        assign_fields = self._get_assign_fields()
        is_assigned = (operator == "=") == value
        if is_assigned:
            return Domain.OR(Domain(field, "!=", False) for field in assign_fields)
        else:
            return Domain.AND(Domain(field, "=", False) for field in assign_fields)

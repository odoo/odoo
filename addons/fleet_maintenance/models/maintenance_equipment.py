# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    equipment_assign_to = fields.Selection(selection_add=[('vehicle', 'Vehicle')], required=True,
        ondelete={'vehicle': 'set other'}, default='vehicle')
    vehicle_id = fields.Many2one('fleet.vehicle', compute='_compute_equipment_assignment_fields',
        store=True, readonly=False, string="Vehicle", index='btree_not_null', tracking=True)

    @api.depends(lambda self: self._get_assign_fields())
    def _compute_is_assigned(self):
        assign_fields = self._get_assign_fields()
        for equipment in self:
            equipment.is_assigned = any(equipment[field] for field in assign_fields)

    def _get_assign_fields(self):
        return super()._get_assign_fields() + ['vehicle_id']

    def _get_owner_methods_by_equipment_assign_to(self):
        owner_methods = super()._get_owner_methods_by_equipment_assign_to()
        owner_methods.update({
            'vehicle': lambda eq: eq.vehicle_id.manager_id.id or self.env.user.id,
        })
        return owner_methods

    def _get_assignment_handlers_by_equipment_assign_to(self):
        handlers = super()._get_assignment_handlers_by_equipment_assign_to()
        handlers.update({
            'vehicle': lambda eq: {
                field: eq[field] if field == 'vehicle_id' else False
                for field in self._get_assign_fields()
            },
        })
        return handlers

    def _search_is_assigned(self, operator, value):
        if operator not in ('=', '!=') or value not in (True, False):
            return NotImplemented
        assign_fields = self._get_assign_fields()
        is_equipment_assigned = (operator == "=") == value
        if is_equipment_assigned:
            return Domain.OR(Domain(field, "!=", False) for field in assign_fields)
        return Domain.AND(Domain(field, "=", False) for field in assign_fields)

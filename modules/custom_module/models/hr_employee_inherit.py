from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    allowed_floor_ids = fields.Many2many(
        'restaurant.floor',
        'hr_employee_floor_rel',
        'employee_id',
        'floor_id',
        string='Floors autorisés',
        groups="point_of_sale.group_pos_user"
    )

    def _load_pos_data_fields(self, pos_config_id):
        fields = super()._load_pos_data_fields(pos_config_id)
        if 'allowed_floor_ids' not in fields:
            fields.append('allowed_floor_ids')
        return fields

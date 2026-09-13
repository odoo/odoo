from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    equipment_ids = fields.One2many(
        comodel_name="maintenance.equipment",
        inverse_name="employee_id",
        groups="hr.group_hr_user",
    )
    equipment_count = fields.Count(count_of="equipment_ids")

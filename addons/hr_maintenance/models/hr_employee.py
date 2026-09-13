from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    equipment_ids = fields.One2many(
        "maintenance.equipment", "employee_id", groups="hr.group_hr_user"
    )
    equipment_count = fields.Count("equipment_ids")

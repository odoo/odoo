from odoo import fields, models


class ResourceScheduleException(models.Model):
    _inherit = "resource.schedule.exception"

    work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type",
        groups="hr.group_hr_user",
    )

    def _copy_leave_vals(self):
        res = super()._copy_leave_vals()
        res["work_entry_type_id"] = self.work_entry_type_id.id
        return res

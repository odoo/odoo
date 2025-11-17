from odoo import fields, models


class HrPublicHolidayLeave(models.Model):
    _inherit = 'hr.public.holiday.leave'

    work_entry_type_id = fields.Many2one("hr.work.entry.type", "Work Entry Type", groups="hr.group_hr_user")

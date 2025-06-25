from odoo import fields, models


class HrLeavePublicHoliday(models.Model):
    _inherit = 'hr.leave.public.holiday'

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Work Entry Type',
        groups="hr.group_hr_user",
        help="The type of work entry to create for this public holiday.")

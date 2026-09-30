# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Work Entry Type',
        groups="hr.group_hr_user")

    def _copy_leave_vals(self):
        res = super()._copy_leave_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res

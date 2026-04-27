# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    group_s_code = fields.Char(
        "Group S code", groups="hr.group_hr_user", compute='_compute_group_s_code',
        store=True, readonly=False)

    @api.constrains('group_s_code')
    def _check_ucm_code(self):
        if any(entry_type.group_s_code and len(entry_type.group_s_code) > 3 for entry_type in self):
            raise ValidationError(_("The code shouldn't exceed 3 characters!"))

    @api.onchange('group_s_code')
    def _compute_group_s_code(self):
        for work_entry_type in self:
            if not work_entry_type.group_s_code or len(work_entry_type.group_s_code) >= 3:
                continue
            work_entry_type.group_s_code = work_entry_type.group_s_code.ljust(3)

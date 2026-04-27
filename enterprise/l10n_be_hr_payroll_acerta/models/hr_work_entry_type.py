# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import format_list


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    acerta_code = fields.Char("Acerta code", groups="hr.group_hr_user")

    @api.constrains('acerta_code')
    def _check_acerta_code(self):
        problematic_work_entries = self.env['hr.work.entry.type']
        for we in self:
            if we.acerta_code and not (2 < len(we.acerta_code) < 7):
                problematic_work_entries |= we

        if problematic_work_entries:
            raise ValidationError(_(
                'The following work entry types have an Acerta code that '
                'is not between 3 and 6 characters: %(work_entries)s',
                work_entries=format_list(self.env, problematic_work_entries.mapped('name'))
            ))

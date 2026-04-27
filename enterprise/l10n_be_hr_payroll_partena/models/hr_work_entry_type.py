# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    partena_code = fields.Char(
        "Partena code", groups="hr.group_hr_user")

    @api.constrains('partena_code')
    def _check_partena_code(self):
        if any(we.partena_code and len(we.partena_code) != 5 for we in self):
            raise ValidationError(_('The code should have 5 characters!'))

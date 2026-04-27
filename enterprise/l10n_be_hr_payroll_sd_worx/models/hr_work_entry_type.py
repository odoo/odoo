# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    sdworx_code = fields.Char("SDWorx code", groups="hr.group_hr_user")

    @api.constrains('sdworx_code')
    def _check_sdworx_code(self):
        invalid_work_entry_types = self.filtered(lambda we: we.sdworx_code and len(we.sdworx_code) != 4)
        if invalid_work_entry_types:
            error = _("The following work entry types should have a 4 characters SDWorx code or should be left empty:\n")
            raise ValidationError(error + "\n".join(invalid_work_entry_types.mapped('name')))

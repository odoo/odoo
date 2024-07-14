#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    sdworx_code = fields.Char("SDWorx code", groups="hr.group_hr_user")

    @api.constrains('sdworx_code')
    def _check_sdworx_code(self):
        if self.sdworx_code and len(self.sdworx_code) != 4:
            raise ValidationError(_('The code should have 4 characters!'))

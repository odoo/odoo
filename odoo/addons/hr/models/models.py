# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, tools, _
from odoo.addons.mail.tools.alias_error import AliasError


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _alias_get_error(self, message, message_dict, alias):
        if alias.alias_contact == 'employees':
            email_from = tools.decode_message_header(message, 'From')
            email_address = tools.email_split(email_from)[0]
            employee = self.env['hr.employee'].search([('work_email', 'ilike', email_address)], limit=1)
            if not employee:
                employee = self.env['hr.employee'].search([('user_id.email', 'ilike', email_address)], limit=1)
            if not employee:
                return AliasError('error_hr_employee_restricted', _('restricted to employees'))
            return False
        return super(BaseModel, self)._alias_get_error(message, message_dict, alias)

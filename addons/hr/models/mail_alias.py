# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, _


class Alias(models.Model):
    _inherit = 'mail.alias'

    alias_contact = fields.Selection(selection_add=[
        ('employees', 'Authenticated Employees'),
    ], ondelete={'employees': 'cascade'})

    def _get_alias_bounced_body_fallback(self, message_dict):
        if self.alias_contact == 'employees':
            return _("""Hi,<br/>
Your document has not been created because your email address is not recognized.<br/>
Please send emails with the email address recorded on your employee information, or contact your HR manager.""")
        else:
            return super(Alias, self)._get_alias_bounced_body_fallback(message_dict)


class AliasMixin(models.AbstractModel):
    _inherit = 'mail.alias.mixin'

    def _alias_check_contact_on_record(self, record, message, message_dict, alias):
        if alias.alias_contact == 'employees':
            email_from = tools.decode_message_header(message, 'From')
            email_address = tools.email_split(email_from)[0]
            employee = self.env['hr.employee'].search([('work_email', 'ilike', email_address)], limit=1)
            if not employee:
                employee = self.env['hr.employee'].search([('user_id.email', 'ilike', email_address)], limit=1)
            if not employee:
                return _('restricted to employees')
            return True
        return super(AliasMixin, self)._alias_check_contact_on_record(record, message, message_dict, alias)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


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
        return super(Alias, self)._get_alias_bounced_body_fallback(message_dict)

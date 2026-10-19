# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, tools
from odoo.tools.misc import str2bool
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def web_create_users(self, emails):
        emails_normalized = [tools.mail.parse_contact_from_email(email)[1] for email in emails]

        if 'email_normalized' not in self._fields:
            raise UserError(self.env._("You have to install the Discuss application to use this feature."))

        # Reactivate already existing users if needed
        deactivated_users = self.with_context(active_test=False).search([
            ('active', '=', False),
            '|', ('login', 'in', emails + emails_normalized), ('email_normalized', 'in', emails_normalized)])
        for user in deactivated_users:
            user.active = True
        done = deactivated_users.mapped('email_normalized')

        new_emails = set(emails) - set(deactivated_users.mapped('email'))

        # Process new email addresses : create new users
        for email in new_emails:
            name, email_normalized = tools.mail.parse_contact_from_email(email)
            if email_normalized in done:
                continue
            default_values = {'login': email_normalized, 'name': name or email_normalized, 'email': email_normalized, 'active': True}
            user = self.with_context(signup_valid=True).create(default_values)

        return True

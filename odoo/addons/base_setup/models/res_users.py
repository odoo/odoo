# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, tools
from odoo.tools.misc import str2bool


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def web_create_users(self, emails):
        emails_normalized = [tools.mail.parse_contact_from_email(email)[1] for email in emails]

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

    def _default_groups(self):
        """Default groups for employees

        If base_setup.default_user_minimal is set, only the "Employee" group is used
        """
        if str2bool(self.env['ir.config_parameter'].sudo().get_param("base_setup.default_user_rights_minimal"), default=False):
            employee_group = self.env.ref("base.group_user")
            # force the trans_implied_ids during default for consistency in the interface
            return employee_group | employee_group.trans_implied_ids
        return super()._default_groups()

    def _apply_groups_to_existing_employees(self):
        """
        If base_setup.default_user_rights_minimal is set, do not apply any new groups to existing employees
        """
        if str2bool(self.env['ir.config_parameter'].sudo().get_param("base_setup.default_user_rights_minimal"), default=False):
            return False
        return super()._apply_groups_to_existing_employees()

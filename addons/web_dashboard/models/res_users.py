# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from openerp import models, api, _
from openerp.exceptions import RedirectWarning
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def web_dashboard_create_users(self, emails, optional_message=""):

        # Also search for active = False
        existing_users = self.with_context(active_test=False).search([('login', 'in', emails)])

        # Process existing users
        for user in existing_users:
            if not user.login_date and not user.signup_valid:
                user.action_reset_password()
            else:
                # Already a user, to reactivate if desactivated
                user.active = True

        new_emails = set(emails) - set(existing_users.mapped('email'))
        template_user_id = self.env['ir.config_parameter'].get_param('auth_signup.template_user_id', 'False')

        # Process new email addresses : create new users
        for email in new_emails:
            default_values = {'login': email, 'name': email, 'email': email, 'active': True}
            if template_user_id:
                user = self.with_context(custom_message=optional_message, create_user=1).browse(int(template_user_id)).copy(default=default_values)
            else:
                user = self.with_context(custom_message=optional_message, create_user=1).create(default_values)
            # If outgoing mail server is not properly configured (signup_token is set to False in this case)
            if not user.signup_token:
                action = self.env.ref('base.action_ir_mail_server_list')
                msg = _('Outgoing mail server is not configured properly, You should configure it before inviting users. \nPlease go to Outgoing Mail Servers.')
                raise RedirectWarning(msg, action.id, _('Configure Outgoing Mail Servers'))
            else:
                # Increase expiration date by one month
                dt = datetime.now() + timedelta(months=1)
                user.write({'signup_expiration': dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return {'status': 'success'}

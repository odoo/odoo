# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from openerp import models, api, _
from openerp.exceptions import RedirectWarning
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class Users(models.Model):
    _inherit = 'res.users'

    def web_dashboard_get_users_by_state(self):
        users = self.search([('login_date', '=', False)], order="create_date desc")
        pending = users.filtered(lambda u: u.signup_valid)
        expired = users - pending
        return {'expired': zip(expired.mapped('id'), expired.mapped('login')), 'pending': zip(pending.mapped('id'), pending.mapped('login'))}

    @api.model
    def web_dashboard_create_users(self, emails, optional_message=""):
        existing_users = self.search(['&', ('login', 'in', emails), '|', ('active', '=', True), ('active', '=', False)])
        #Processing existing users
        for user in existing_users:
            if user.login_date == False and not user.signup_valid:
                user.action_reset_password()
            else:
                #Already a user, reactivated in case it is deactivated
                user.active = True
        new_emails = set(emails) - set(existing_users.mapped('login'))
        #Processing new email addresses : create new users (Used template user)
        template_user_id = self.env['ir.config_parameter'].get_param('auth_signup.template_user_id', 'False')
        for email in new_emails:
            default_values = {'login': email, 'name': email, 'email': email, 'active': True}
            if template_user_id:
                user = self.with_context(custom_message=optional_message, create_user=1).browse(int(template_user_id)).copy(default=default_values)
            else:
                user = self.with_context(custom_message=optional_message, create_user=1).create(default_values)
            # if user haven't configured Outgoing mail server properly.
            if user.signup_token == False:
                action = self.env.ref('base.action_ir_mail_server_list')
                msg = _('Outgoing mail server is not configured properly, You should configure it before inviting users. \nPlease go to Outgoing Mail Servers.')
                raise RedirectWarning(msg, action.id, _('Configure Outgoing Mail Servers'))
            else:
                # increase expiration days by 30 day because 1 day is not enough
                dt = datetime.now() + timedelta(days=30)
                user.write({'signup_expiration': dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return {'status': 'success'}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging

from ast import literal_eval
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.auth_signup.models.res_partner import SignupError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    state = fields.Selection(compute='_compute_state', search='_search_state', string='Status',
                 selection=[('new', 'Never Connected'), ('active', 'Confirmed')])

    def _search_state(self, operator, value):
        negative = operator in expression.NEGATIVE_TERM_OPERATORS

        # In case we have no value
        if not value:
            return expression.TRUE_DOMAIN if negative else expression.FALSE_DOMAIN

        if operator in ['in', 'not in']:
            if len(value) > 1:
                return expression.FALSE_DOMAIN if negative else expression.TRUE_DOMAIN
            if value[0] == 'new':
                comp = '!=' if negative else '='
            if value[0] == 'active':
                comp = '=' if negative else '!='
            return [('log_ids', comp, False)]

        if operator in ['=', '!=']:
            # In case we search against anything else than new, we have to invert the operator
            if value != 'new':
                operator = expression.TERM_OPERATORS_NEGATION[operator]

            return [('log_ids', operator, False)]

        return expression.TRUE_DOMAIN

    def _compute_state(self):
        for user in self:
            user.state = 'active' if user.login_date else 'new'

    @api.model
    def signup(self, values, token=None):
        """ signup a user, to either:
            - create a new user (no token), or
            - create a user for a partner (with token, but no user for partner), or
            - change the password of a user (with token, and existing user).
            :param values: a dictionary with field values that are written on user
            :param token: signup token (optional)
            :return: (dbname, login, password) for the signed up user
        """
        if token:
            # signup with a token: find the corresponding partner id
            partner = self.env['res.partner']._signup_retrieve_partner(token, check_validity=True, raise_exception=True)
            # invalidate signup token
            partner.write({'signup_type': False})
            partner_user = partner.user_ids and partner.user_ids[0] or False

            # avoid overwriting existing (presumably correct) values with geolocation data
            if partner.country_id or partner.zip or partner.city:
                values.pop('city', None)
                values.pop('country_id', None)
            if partner.lang:
                values.pop('lang', None)

            if partner_user:
                # user exists, modify it according to values
                values.pop('login', None)
                values.pop('name', None)
                partner_user.write(values)
                if not partner_user.login_date:
                    partner_user._notify_inviter()
                return (partner_user.login, values.get('password'))
            else:
                # user does not exist: sign up invited user
                values.update({
                    'name': partner.name,
                    'partner_id': partner.id,
                    'email': values.get('email') or values.get('login'),
                })
                if partner.company_id:
                    values['company_id'] = partner.company_id.id
                    values['company_ids'] = [(6, 0, [partner.company_id.id])]
                partner_user = self._signup_create_user(values)
                partner_user._notify_inviter()
        else:
            # no token, sign up an external user
            values['email'] = values.get('email') or values.get('login')
            self._signup_create_user(values)

        return (values.get('login'), values.get('password'))

    @api.model
    def _get_signup_invitation_scope(self):
        return self.env['ir.config_parameter'].sudo().get_param('auth_signup.invitation_scope', 'b2b')

    @api.model
    def _signup_create_user(self, values):
        """ signup a new user using the template user """

        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if self._get_signup_invitation_scope() != 'b2c':
                raise SignupError(_('Signup is not allowed for uninvited users'))
        return self._create_user_from_template(values)

    def _notify_inviter(self):
        for user in self:
            # notify invite user that new user is connected
            user.create_uid._bus_send(
                "res.users/connection", {"username": user.name, "partnerId": user.partner_id.id}
            )

    def _create_user_from_template(self, values):
        template_user_id = literal_eval(self.env['ir.config_parameter'].sudo().get_param('base.template_portal_user_id', 'False'))
        template_user = self.browse(template_user_id)
        if not template_user.exists():
            raise ValueError(_('Signup: invalid template user'))

        if not values.get('login'):
            raise ValueError(_('Signup: no login given for new user'))
        if not values.get('partner_id') and not values.get('name'):
            raise ValueError(_('Signup: no name or partner given for new user'))

        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        try:
            with self.env.cr.savepoint():
                return template_user.with_context(no_reset_password=True).copy(values)
        except Exception as e:
            # copy may failed if asked login is not available.
            raise SignupError(str(e))

    def reset_password(self, login):
        """ retrieve the user corresponding to login (login or email),
            and reset their password
        """
        users = self.search(self._get_login_domain(login))
        if not users:
            users = self.search(self._get_email_domain(login))
        if not users:
            raise Exception(_('No account found for this login'))
        if len(users) > 1:
            raise Exception(_('Multiple accounts found for this login'))
        return users.action_reset_password()

    def action_reset_password(self):
        try:
            if self.env.context.get('create_user') == 1:
                return self._action_reset_password(signup_type="signup")
            else:
                return self._action_reset_password(signup_type="reset")
        except MailDeliveryException as mde:
            if len(mde.args) == 2 and isinstance(mde.args[1], ConnectionRefusedError):
                raise UserError(_("Could not contact the mail server, please check your outgoing email server configuration")) from mde
            else:
                raise UserError(_("There was an error when trying to deliver your Email, please check your configuration")) from mde

    def _action_reset_password(self, signup_type="reset"):
        """ create signup token for each user, and send their signup url by email """
        if self.env.context.get('install_mode') or self.env.context.get('import_file'):
            return
        if self.filtered(lambda user: not user.active):
            raise UserError(_("You cannot perform this action on an archived user."))
        # prepare reset password signup
        create_mode = bool(self.env.context.get('create_user'))

        self.mapped('partner_id').signup_prepare(signup_type=signup_type)

        # send email to users with their signup url
        account_created_template = None
        if create_mode:
            account_created_template = self.env.ref('auth_signup.set_password_email', raise_if_not_found=False)
            if account_created_template and account_created_template._name != 'mail.template':
                _logger.error("Wrong set password template %r", account_created_template)
                return

        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'message_type': 'user_notification',
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }

        for user in self:
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.", user.name))
            email_values['email_to'] = user.email
            with contextlib.closing(self.env.cr.savepoint()):
                if account_created_template:
                    account_created_template.send_mail(
                        user.id, force_send=True,
                        raise_exception=True, email_values=email_values)
                else:
                    user_lang = user.lang or self.env.lang or 'en_US'
                    body = self.env['mail.render.mixin'].with_context(lang=user_lang)._render_template(
                        self.env.ref('auth_signup.reset_password_email'),
                        model='res.users', res_ids=user.ids,
                        engine='qweb_view', options={'post_process': True})[user.id]
                    mail = self.env['mail.mail'].sudo().create({
                        'subject': self.with_context(lang=user_lang).env._('Password reset'),
                        'email_from': user.company_id.email_formatted or user.email_formatted,
                        'body_html': body,
                        **email_values,
                    })
                    mail.send()
            if signup_type == 'reset':
                _logger.info("Password reset email sent for user <%s> to <%s>", user.login, user.email)
                message = _('A reset password link was sent by email')
            else:
                _logger.info("Signup email sent for user <%s> to <%s>", user.login, user.email)
                message = _('A signup link was sent by email')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Notification',
                'message': message,
                'sticky': False
            }
        }

    def send_unregistered_user_reminder(self, *, after_days=5, batch_size=100):
        email_template = self.env.ref('auth_signup.mail_template_data_unregistered_users', raise_if_not_found=False)
        if not email_template:
            _logger.warning("Template 'auth_signup.mail_template_data_unregistered_users' was not found. Cannot send reminder notifications.")
            self.env['ir.cron']._commit_progress(deactivate=True)
            return
        datetime_min = fields.Datetime.today() - relativedelta(days=after_days)
        datetime_max = datetime_min + relativedelta(days=1)

        invited_by_users = self.search_fetch([
            ('share', '=', False),
            ('create_uid.email', '!=', False),
            ('create_date', '>=', datetime_min),
            ('create_date', '<', datetime_max),
            ('log_ids', '=', False),
        ], ['name', 'login', 'create_uid']).grouped('create_uid')

        # Do not use progress since we have no way of knowing to whom we have
        # already sent e-mails.

        done = 0
        for user, invited_users in invited_by_users.items():
            invited_user_emails = [f"{u.name} ({u.login})" for u in invited_users]
            template = email_template.with_context(dbname=self.env.cr.dbname, invited_users=invited_user_emails)
            template.send_mail(user.id, email_layout_xmlid='mail.mail_notification_light', force_send=False)
            done += len(invited_users)
            # do not set remaining and the search will return always the same users!
            self.env['ir.cron']._notify_progress(done=done, remaining=0)
            self.env.cr.commit()

    @api.model
    def web_create_users(self, emails):
        inactive_users = self.search([('state', '=', 'new'), '|', ('login', 'in', emails), ('email', 'in', emails)])
        new_emails = set(emails) - set(inactive_users.mapped('email'))
        res = super(ResUsers, self).web_create_users(list(new_emails))
        if inactive_users:
            inactive_users.with_context(create_user=True).action_reset_password()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # overridden to automatically invite user to sign up
        users = super(ResUsers, self).create(vals_list)
        if not self.env.context.get('no_reset_password'):
            users_with_email = users.filtered('email')
            if users_with_email:
                try:
                    users_with_email.with_context(create_user=True)._action_reset_password(signup_type='signup')
                except MailDeliveryException:
                    users_with_email.partner_id.with_context(create_user=True).signup_cancel()
        return users

    def copy(self, default=None):
        if not default or not default.get('email'):
            # avoid sending email to the user we are duplicating
            self = self.with_context(no_reset_password=True)
        return super().copy(default=default)

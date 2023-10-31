# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import ustr

from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.addons.auth_signup.models.res_partner import SignupError, now

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
            partner.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})

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
                return (self.env.cr.dbname, partner_user.login, values.get('password'))
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

        return (self.env.cr.dbname, values.get('login'), values.get('password'))

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
            invite_partner = user.create_uid.partner_id
            if invite_partner:
                # notify invite user that new user is connected
                self.env['bus.bus']._sendone(invite_partner, 'res.users/connection', {
                    'username': user.name,
                    'partnerId': user.partner_id.id,
                })

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
            raise SignupError(ustr(e))

    def reset_password(self, login):
        """ retrieve the user corresponding to login (login or email),
            and reset their password
        """
        users = self.search([('login', '=', login)])
        if not users:
            users = self.search([('email', '=', login)])
        if len(users) != 1:
            raise Exception(_('Reset password: invalid username or email'))
        return users.action_reset_password()

    def action_reset_password(self):
        """ create signup token for each user, and send their signup url by email """
        if self.env.context.get('install_mode', False):
            return
        if self.filtered(lambda user: not user.active):
            raise UserError(_("You cannot perform this action on an archived user."))
        # prepare reset password signup
        create_mode = bool(self.env.context.get('create_user'))

        # no time limit for initial invitation, only for reset password
        expiration = False if create_mode else now(days=+1)

        self.mapped('partner_id').signup_prepare(signup_type="reset", expiration=expiration)

        # send email to users with their signup url
        template = False
        if create_mode:
            try:
                template = self.env.ref('auth_signup.set_password_email', raise_if_not_found=False)
            except ValueError:
                pass
        if not template:
            template = self.env.ref('auth_signup.reset_password_email')
        assert template._name == 'mail.template'

        email_values = {
            'email_cc': False,
            'auto_delete': True,
            'recipient_ids': [],
            'partner_ids': [],
            'scheduled_date': False,
        }

        for user in self:
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.", user.name))
            email_values['email_to'] = user.email
            # TDE FIXME: make this template technical (qweb)
            with self.env.cr.savepoint():
                force_send = not(self.env.context.get('import_file', False))
                template.send_mail(user.id, force_send=force_send, raise_exception=True, email_values=email_values)
            _logger.info("Password reset email sent for user <%s> to <%s>", user.login, user.email)

    def send_unregistered_user_reminder(self, after_days=5):
        datetime_min = fields.Datetime.today() - relativedelta(days=after_days)
        datetime_max = datetime_min + relativedelta(hours=23, minutes=59, seconds=59)

        res_users_with_details = self.env['res.users'].search_read([
            ('share', '=', False),
            ('create_uid.email', '!=', False),
            ('create_date', '>=', datetime_min),
            ('create_date', '<=', datetime_max),
            ('log_ids', '=', False)], ['create_uid', 'name', 'login'])

        # group by invited by
        invited_users = defaultdict(list)
        for user in res_users_with_details:
            invited_users[user.get('create_uid')[0]].append("%s (%s)" % (user.get('name'), user.get('login')))

        # For sending mail to all the invitors about their invited users
        for user in invited_users:
            template = self.env.ref('auth_signup.mail_template_data_unregistered_users').with_context(dbname=self._cr.dbname, invited_users=invited_users[user])
            template.send_mail(user, notif_layout='mail.mail_notification_light', force_send=False)

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
                    users_with_email.with_context(create_user=True).action_reset_password()
                except MailDeliveryException:
                    users_with_email.partner_id.with_context(create_user=True).signup_cancel()
        return users

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        sup = super(ResUsers, self)
        if not default or not default.get('email'):
            # avoid sending email to the user we are duplicating
            sup = super(ResUsers, self.with_context(no_reset_password=True))
        return sup.copy(default=default)

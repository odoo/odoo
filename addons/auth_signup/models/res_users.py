# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import logging

from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import ustr
from odoo.http import request

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

    @classmethod
    def authenticate(cls, db, login, password, user_agent_env):
        uid = super().authenticate(db, login, password, user_agent_env)
        try:
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, uid, {})
                if env.user._should_alert_new_device():
                    env.user._alert_new_device()
        except MailDeliveryException:
            pass
        return uid

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
            raise Exception(_('No account found for this login'))
        return users.action_reset_password()

    def action_reset_password(self):
        try:
            return self._action_reset_password()
        except MailDeliveryException as mde:
            if len(mde.args) == 2 and isinstance(mde.args[1], ConnectionRefusedError):
                raise UserError(_("Could not contact the mail server, please check your outgoing email server configuration")) from mde
            else:
                raise UserError(_("There was an error when trying to deliver your Email, please check your configuration")) from mde

    def _action_reset_password(self):
        """ create signup token for each user, and send their signup url by email """
        if self.env.context.get('install_mode') or self.env.context.get('import_file'):
            return
        if self.filtered(lambda user: not user.active):
            raise UserError(_("You cannot perform this action on an archived user."))
        # prepare reset password signup
        create_mode = bool(self.env.context.get('create_user'))

        # no time limit for initial invitation, only for reset password
        expiration = False if create_mode else now(days=+1)

        self.mapped('partner_id').signup_prepare(signup_type="reset", expiration=expiration)

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
                    body = self.env['mail.render.mixin']._render_template(
                        self.env.ref('auth_signup.reset_password_email'),
                        model='res.users', res_ids=user.ids,
                        engine='qweb_view', options={'post_process': True})[user.id]
                    mail = self.env['mail.mail'].sudo().create({
                        'subject': _('Password reset'),
                        'email_from': user.company_id.email_formatted or user.email_formatted,
                        'body_html': body,
                        **email_values,
                    })
                    mail.send()
            _logger.info("Password reset email sent for user <%s> to <%s>", user.login, user.email)

    def send_unregistered_user_reminder(self, after_days=5):
        email_template = self.env.ref('auth_signup.mail_template_data_unregistered_users', raise_if_not_found=False)
        if not email_template:
            _logger.warning("Template 'auth_signup.mail_template_data_unregistered_users' was not found. Cannot send reminder notifications.")
            return
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
            template = email_template.with_context(dbname=self._cr.dbname, invited_users=invited_users[user])
            template.send_mail(user, email_layout_xmlid='mail.mail_notification_light', force_send=False)

    def _alert_new_device(self):
        self.ensure_one()
        if self.email:
            email_values = {
                'email_cc': False,
                'auto_delete': True,
                'message_type': 'user_notification',
                'recipient_ids': [],
                'partner_ids': [],
                'scheduled_date': False,
                'email_to': self.email
            }

            body = self.env['mail.render.mixin']._render_template(
                    'auth_signup.alert_login_new_device',
                    model='res.users', res_ids=self.ids,
                    engine='qweb_view', options={'post_process': True},
                    add_context=self._prepare_new_device_notice_values())[self.id]
            mail = self.env['mail.mail'].sudo().create({
                'subject': _('New Connection to your Account'),
                'email_from': self.company_id.email_formatted or self.email_formatted,
                'body_html': body,
                **email_values,
            })
            mail.send()
            _logger.info("New device alert email sent for user <%s> to <%s>", self.login, self.email)

    def _prepare_new_device_notice_values(self):
        values = {
            'login_date': fields.Datetime.now(),
            'location_address': False,
            'ip_address': False,
            'browser': False,
            'useros': False,
        }

        if not request:
            return values

        city = request.geoip.get('city') or False
        region = request.geoip.get('region_name') or False
        country = request.geoip.get('country') or False
        if country:
            if region and city:
                values['location_address'] = _("Near %(city)s, %(region)s, %(country)s", city=city, region=region, country=country)
            elif region:
                values['location_address'] = _("Near %(region)s, %(country)s", region=region, country=country)
            else:
                values['location_address'] = _("In %(country)s", country=country)
        else:
            values['location_address'] = False
        values['ip_address'] = request.httprequest.environ['REMOTE_ADDR']
        if request.httprequest.user_agent:
            if request.httprequest.user_agent.browser:
                values['browser'] = request.httprequest.user_agent.browser.capitalize()
            if request.httprequest.user_agent.platform:
                values['useros'] = request.httprequest.user_agent.platform.capitalize()
        return values

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
                    users_with_email.with_context(create_user=True)._action_reset_password()
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

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import ustr

from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.addons.auth_signup.models.res_partner import SignupError, now

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    state = fields.Selection(compute='_compute_state', string='Status',
                 selection=[('new', 'Never Connected'), ('active', 'Confirmed')])

    @api.multi
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
                self._signup_create_user(values)
        else:
            # no token, sign up an external user
            values['email'] = values.get('email') or values.get('login')
            self._signup_create_user(values)

        return (self.env.cr.dbname, values.get('login'), values.get('password'))

    @api.model
    def _signup_create_user(self, values):
        """ create a new user from the template user """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        template_user_id = literal_eval(get_param('auth_signup.template_user_id', 'False'))
        template_user = self.browse(template_user_id)
        assert template_user.exists(), 'Signup: invalid template user'

        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if not literal_eval(get_param('auth_signup.allow_uninvited', 'False')):
                raise SignupError(_('Signup is not allowed for uninvited users'))

        assert values.get('login'), "Signup: no login given for new user"
        assert values.get('partner_id') or values.get('name'), "Signup: no name or partner given for new user"

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

    @api.multi
    def action_reset_password(self):
        """ create signup token for each user, and send their signup url by email """
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

        for user in self:
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.") % user.name)
            template.with_context(lang=user.lang).send_mail(user.id, force_send=True, raise_exception=True)
            _logger.info("Password reset email sent for user <%s> to <%s>", user.login, user.email)

    @api.model
    def create(self, values):
        # overridden to automatically invite user to sign up
        user = super(ResUsers, self).create(values)
        if user.email and not self.env.context.get('no_reset_password'):
            try:
                user.with_context(create_user=True).action_reset_password()
            except MailDeliveryException:
                user.partner_id.with_context(create_user=True).signup_cancel()
        return user

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        sup = super(ResUsers, self)
        if not default or not default.get('email'):
            # avoid sending email to the user we are duplicating
            sup = super(ResUsers, self.with_context(reset_password=False))
        return sup.copy(default=default)

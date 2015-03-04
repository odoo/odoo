# -*- coding: utf-8 -*-

import random
import werkzeug
from ast import literal_eval
from datetime import datetime, timedelta
from urlparse import urljoin

from openerp import api, fields, models, _
from openerp.addons.base.ir.ir_mail_server import MailDeliveryException
from openerp.exceptions import UserError
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, ustr


class SignupError(Exception):
    pass


def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(chars) for i in xrange(20))

def now(**kwargs):
    dt = datetime.now() + timedelta(**kwargs)
    return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def _get_signup_valid(self):
        for partner in self:
            partner.signup_valid = bool(partner.signup_token) and \
            (not partner.signup_expiration or now() <= partner.signup_expiration)

    @api.v8
    def _get_signup_url_for_action(self, action=None, view_type=None, menu_id=None, res_id=None, model=None):
        return self._model._get_signup_url_for_action(self._cr, self._uid, self.ids, action=action,
                                                      view_type=view_type,menu_id=menu_id, res_id=res_id, model=model,
                                                      context=self.env.context)

    @api.v7
    def _get_signup_url_for_action(self, cr, uid, ids, action=None, view_type=None, menu_id=None, res_id=None,
                                   model=None, context=None):
        """ generate a signup url for the given partner ids and action, possibly overriding
            the url state components (menu_id, id, view_type) """
        if context is None:
            context= {}
        res = dict.fromkeys(ids, False)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        for partner in self.browse(cr, uid, ids, context):
            # when required, make sure the partner has a valid signup token
            if context.get('signup_valid') and not partner.user_ids:
                self.signup_prepare(cr, uid, [partner.id], context=context)

            route = 'login'
            # the parameters to encode for the query
            query = dict(db=cr.dbname)
            signup_type = context.get('signup_force_type_in_url', partner.signup_type or '')
            if signup_type:
                route = 'reset_password' if signup_type == 'reset' else signup_type

            if partner.signup_token and signup_type:
                query['token'] = partner.signup_token
            elif partner.user_ids:
                query['login'] = partner.user_ids[0].login
            else:
                continue        # no signup token, no user, thus no signup url!

            fragment = dict()
            if action:
                fragment['action'] = action
            if view_type:
                fragment['view_type'] = view_type
            if menu_id:
                fragment['menu_id'] = menu_id
            if model:
                fragment['model'] = model
            if res_id:
                fragment['id'] = res_id

            if fragment:
                query['redirect'] = '/web#' + werkzeug.url_encode(fragment)

            res[partner.id] = urljoin(base_url, "/web/%s?%s" % (route, werkzeug.url_encode(query)))
        return res

    @api.one
    def _get_signup_url(self):
        """ proxy for function field towards actual implementation """
        self.signup_url = self._get_signup_url_for_action()[self.id]

    signup_token = fields.Char(copy=False)
    signup_type = fields.Char(string='Signup Token Type', copy=False)
    signup_expiration = fields.Datetime(copy=False)
    signup_valid = fields.Boolean(compute='_get_signup_valid', string='Signup Token is Valid')
    signup_url = fields.Char(compute='_get_signup_url', string='Signup URL')

    @api.multi
    def action_signup_prepare(self):
        return self.signup_prepare()

    @api.multi
    def signup_cancel(self):
        return self.write({'signup_token': False, 'signup_type': False, 'signup_expiration': False})

    @api.multi
    def signup_prepare(self, signup_type="signup", expiration=False):
        """ generate a new token for the partners with the given validity, if necessary
            :param expiration: the expiration datetime of the token (string, optional)
        """
        for partner in self:
            if expiration or not partner.signup_valid:
                token = random_token()
                while self._signup_retrieve_partner(token):
                    token = random_token()
                partner.write({'signup_token': token, 'signup_type': signup_type, 'signup_expiration': expiration})
        return True

    def _signup_retrieve_partner(self, token, check_validity=False, raise_exception=False):
        """ find the partner corresponding to a token, and possibly check its validity
            :param token: the token to resolve
            :param check_validity: if True, also check validity
            :param raise_exception: if True, raise exception instead of returning False
            :return: partner (browse record) or False (if raise_exception is False)
        """
        partner = self.search([('signup_token', '=', token)], limit=1)
        if not partner:
            if raise_exception:
                raise SignupError("Signup token '%s' is not valid" % token)
            return False
        if check_validity and not partner.signup_valid:
            if raise_exception:
                raise SignupError("Signup token '%s' is no longer valid" % token)
            return False
        return partner

    @api.model
    def signup_retrieve_info(self, token):
        """ retrieve the user info about the token
            :return: a dictionary with the user information:
                - 'db': the name of the database
                - 'token': the token, if token is valid
                - 'name': the name of the partner, if token is valid
                - 'login': the user login, if the user already exists
                - 'email': the partner email, if the user does not exist
        """
        partner = self._signup_retrieve_partner(token, raise_exception=True)
        res = {'db': self.env.cr.dbname}
        if partner.signup_valid:
            res['token'] = token
            res['name'] = partner.name
        if partner.user_ids:
            res['login'] = partner.user_ids[0].login
        else:
            res['email'] = partner.email or ''
        return res


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.depends('login_date')
    def _get_state(self):
        for user in self:
            user.state = ('active' if user.login_date else 'new')

    state = fields.Selection(compute='_get_state', string='Status',
                             selection=[('new', 'Never Connected'), ('active', 'Activated')])

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

    def _signup_create_user(self, values):
        """ create a new user from the template user """
        IrConfigParam = self.env['ir.config_parameter']
        template_user_id = literal_eval(IrConfigParam.get_param('auth_signup.template_user_id', 'False'))
        template_user = self.browse(template_user_id)
        assert template_user_id and template_user.exists(), 'Signup: invalid template user'

        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if not literal_eval(IrConfigParam.get_param('auth_signup.allow_uninvited', 'False')):
                raise SignupError('Signup is not allowed for uninvited users')

        assert values.get('login'), "Signup: no login given for new user"
        assert values.get('partner_id') or values.get('name'), "Signup: no name or partner given for new user"

        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        try:
            with self.env.cr.savepoint():
                return template_user.with_context(no_reset_password=True).copy(values)
        except Exception, e:
            # copy may failed if asked login is not available.
            raise SignupError(ustr(e))

    @api.model
    def reset_password(self, login):
        """ retrieve the user corresponding to login (login or email),
            and reset their password
        """
        users = self.search([('login', '=', login)])
        if not users:
            users = self.search([('email', '=', login)])
        if len(users) != 1:
            raise Exception('Reset password: invalid username or email')
        return users.action_reset_password()

    @api.multi
    def action_reset_password(self):
        """ create signup token for each user, and send their signup url by email """
        # prepare reset password signup
        self.mapped('partner_id').signup_prepare(signup_type="reset", expiration=now(days=+1))

        # send email to users with their signup url
        template = False
        if self.env.context.get('create_user'):
            try:
                template = self.env.ref('auth_signup.set_password_email')
            except ValueError:
                pass
        if not bool(template):
            template = self.env.ref('auth_signup.reset_password_email')
        assert template._name == 'mail.template'

        for user in self:
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.") % user.name)
            template.send_mail(user.id, force_send=True, raise_exception=True)

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

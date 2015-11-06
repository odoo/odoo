# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
import random
from urlparse import urljoin
import werkzeug

from openerp.addons.base.ir.ir_mail_server import MailDeliveryException
from openerp.osv import osv, fields
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT, ustr
from ast import literal_eval
from openerp.tools.translate import _
from openerp.exceptions import UserError

class SignupError(Exception):
    pass

def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.SystemRandom().choice(chars) for i in xrange(20))

def now(**kwargs):
    dt = datetime.now() + timedelta(**kwargs)
    return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


class res_partner(osv.Model):
    _inherit = 'res.partner'

    def _get_signup_valid(self, cr, uid, ids, name, arg, context=None):
        dt = now()
        res = {}
        for partner in self.browse(cr, uid, ids, context):
            res[partner.id] = bool(partner.signup_token) and \
                                (not partner.signup_expiration or dt <= partner.signup_expiration)
        return res

    def _get_signup_url_for_action(self, cr, uid, ids, action=None, view_type=None, menu_id=None, res_id=None, model=None, context=None):
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
            base = '/web#'
            if action == '/mail/view':
                base = '/mail/view?'
            elif action:
                fragment['action'] = action
            if view_type:
                fragment['view_type'] = view_type
            if menu_id:
                fragment['menu_id'] = menu_id
            if model:
                fragment['model'] = model
            if res_id:
                fragment['res_id'] = res_id

            if fragment:
                query['redirect'] = base + werkzeug.url_encode(fragment)

            res[partner.id] = urljoin(base_url, "/web/%s?%s" % (route, werkzeug.url_encode(query)))

        return res

    def _get_signup_url(self, cr, uid, ids, name, arg, context=None):
        """ proxy for function field towards actual implementation """
        return self._get_signup_url_for_action(cr, uid, ids, context=context)

    _columns = {
        'signup_token': fields.char('Signup Token', copy=False),
        'signup_type': fields.char('Signup Token Type', copy=False),
        'signup_expiration': fields.datetime('Signup Expiration', copy=False),
        'signup_valid': fields.function(_get_signup_valid, type='boolean', string='Signup Token is Valid'),
        'signup_url': fields.function(_get_signup_url, type='char', string='Signup URL'),
    }

    def action_signup_prepare(self, cr, uid, ids, context=None):
        return self.signup_prepare(cr, uid, ids, context=context)

    def signup_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'signup_token': False, 'signup_type': False, 'signup_expiration': False}, context=context)

    def signup_prepare(self, cr, uid, ids, signup_type="signup", expiration=False, context=None):
        """ generate a new token for the partners with the given validity, if necessary
            :param expiration: the expiration datetime of the token (string, optional)
        """
        for partner in self.browse(cr, uid, ids, context):
            if expiration or not partner.signup_valid:
                token = random_token()
                while self._signup_retrieve_partner(cr, uid, token, context=context):
                    token = random_token()
                partner.write({'signup_token': token, 'signup_type': signup_type, 'signup_expiration': expiration})
        return True

    def _signup_retrieve_partner(self, cr, uid, token,
            check_validity=False, raise_exception=False, context=None):
        """ find the partner corresponding to a token, and possibly check its validity
            :param token: the token to resolve
            :param check_validity: if True, also check validity
            :param raise_exception: if True, raise exception instead of returning False
            :return: partner (browse record) or False (if raise_exception is False)
        """
        partner_ids = self.search(cr, uid, [('signup_token', '=', token)], context=context)
        if not partner_ids:
            if raise_exception:
                raise SignupError("Signup token '%s' is not valid" % token)
            return False
        partner = self.browse(cr, uid, partner_ids[0], context)
        if check_validity and not partner.signup_valid:
            if raise_exception:
                raise SignupError("Signup token '%s' is no longer valid" % token)
            return False
        return partner

    def signup_retrieve_info(self, cr, uid, token, context=None):
        """ retrieve the user info about the token
            :return: a dictionary with the user information:
                - 'db': the name of the database
                - 'token': the token, if token is valid
                - 'name': the name of the partner, if token is valid
                - 'login': the user login, if the user already exists
                - 'email': the partner email, if the user does not exist
        """
        partner = self._signup_retrieve_partner(cr, uid, token, raise_exception=True, context=None)
        res = {'db': cr.dbname}
        if partner.signup_valid:
            res['token'] = token
            res['name'] = partner.name
        if partner.user_ids:
            res['login'] = partner.user_ids[0].login
        else:
            res['email'] = res['login'] = partner.email or ''
        return res

class res_users(osv.Model):
    _inherit = 'res.users'

    def _get_state(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for user in self.browse(cr, uid, ids, context):
            res[user.id] = ('active' if user.login_date else 'new')
        return res

    _columns = {
        'state': fields.function(_get_state, string='Status', type='selection',
                    selection=[('new', 'Never Connected'), ('active', 'Connected')]),
    }

    def signup(self, cr, uid, values, token=None, context=None):
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
            res_partner = self.pool.get('res.partner')
            partner = res_partner._signup_retrieve_partner(
                            cr, uid, token, check_validity=True, raise_exception=True, context=None)
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
                return (cr.dbname, partner_user.login, values.get('password'))
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
                self._signup_create_user(cr, uid, values, context=context)
        else:
            # no token, sign up an external user
            values['email'] = values.get('email') or values.get('login')
            self._signup_create_user(cr, uid, values, context=context)

        return (cr.dbname, values.get('login'), values.get('password'))

    def _signup_create_user(self, cr, uid, values, context=None):
        """ create a new user from the template user """
        ir_config_parameter = self.pool.get('ir.config_parameter')
        template_user_id = literal_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.template_user_id', 'False'))
        assert template_user_id and self.exists(cr, uid, template_user_id, context=context), 'Signup: invalid template user'

        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if not literal_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.allow_uninvited', 'False')):
                raise SignupError('Signup is not allowed for uninvited users')

        assert values.get('login'), "Signup: no login given for new user"
        assert values.get('partner_id') or values.get('name'), "Signup: no name or partner given for new user"

        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        context = dict(context or {}, no_reset_password=True)
        try:
            with cr.savepoint():
                return self.copy(cr, uid, template_user_id, values, context=context)
        except Exception, e:
            # copy may failed if asked login is not available.
            raise SignupError(ustr(e))

    def reset_password(self, cr, uid, login, context=None):
        """ retrieve the user corresponding to login (login or email),
            and reset their password
        """
        user_ids = self.search(cr, uid, [('login', '=', login)], context=context)
        if not user_ids:
            user_ids = self.search(cr, uid, [('email', '=', login)], context=context)
        if len(user_ids) != 1:
            raise Exception(_('Reset password: invalid username or email'))
        return self.action_reset_password(cr, uid, user_ids, context=context)

    def action_reset_password(self, cr, uid, ids, context=None):
        """ create signup token for each user, and send their signup url by email """
        # prepare reset password signup
        res_partner = self.pool.get('res.partner')
        partner_ids = [user.partner_id.id for user in self.browse(cr, uid, ids, context)]
        res_partner.signup_prepare(cr, uid, partner_ids, signup_type="reset", expiration=now(days=+1), context=context)

        if not context:
            context = {}

        # send email to users with their signup url
        template = False
        if context.get('create_user'):
            try:
                # get_object() raises ValueError if record does not exist
                template = self.pool.get('ir.model.data').get_object(cr, uid, 'auth_signup', 'set_password_email')
            except ValueError:
                pass
        if not bool(template):
            template = self.pool.get('ir.model.data').get_object(cr, uid, 'auth_signup', 'reset_password_email')
        assert template._name == 'mail.template'

        for user in self.browse(cr, uid, ids, context):
            if not user.email:
                raise UserError(_("Cannot send email: user %s has no email address.") % user.name)
            self.pool.get('mail.template').send_mail(cr, uid, template.id, user.id, force_send=True, raise_exception=True, context=context)

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        # overridden to automatically invite user to sign up
        user_id = super(res_users, self).create(cr, uid, values, context=context)
        user = self.browse(cr, uid, user_id, context=context)
        if user.email and not context.get('no_reset_password'):
            context = dict(context, create_user=True)
            try:
                self.action_reset_password(cr, uid, [user.id], context=context)
            except MailDeliveryException:
                self.pool.get('res.partner').signup_cancel(cr, uid, [user.partner_id.id], context=context)
        return user_id

    def copy(self, cr, uid, id, default=None, context=None):
        if not default or not default.get('email'):
            # avoid sending email to the user we are duplicating
            context = dict(context or {}, reset_password=False)
        return super(res_users, self).copy(cr, uid, id, default=default, context=context)

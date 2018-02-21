# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import werkzeug.urls

from collections import defaultdict
from datetime import datetime, timedelta

from odoo import api, exceptions, fields, models, _

class SignupError(Exception):
    pass

def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(20))

def now(**kwargs):
    dt = datetime.now() + timedelta(**kwargs)
    return fields.Datetime.to_string(dt)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signup_token = fields.Char(copy=False)
    signup_type = fields.Char(string='Signup Token Type', copy=False)
    signup_expiration = fields.Datetime(copy=False)
    signup_valid = fields.Boolean(compute='_compute_signup_valid', string='Signup Token is Valid')
    signup_url = fields.Char(compute='_compute_signup_url', string='Signup URL')

    @api.multi
    def _compute_signup_valid(self):
        dt = now()
        for partner in self:
            partner.signup_valid = bool(partner.signup_token) and \
            (not partner.signup_expiration or dt <= partner.signup_expiration)

    @api.multi
    def _compute_signup_url(self):
        """ proxy for function field towards actual implementation """
        result = self._get_signup_url_for_action()
        for partner in self:
            partner.signup_url = result.get(partner.id, False)

    @api.multi
    def _get_signup_url_for_action(self, action=None, view_type=None, menu_id=None, res_id=None, model=None):
        """ generate a signup url for the given partner ids and action, possibly overriding
            the url state components (menu_id, id, view_type) """

        res = dict.fromkeys(self.ids, False)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for partner in self:
            # when required, make sure the partner has a valid signup token
            if self.env.context.get('signup_valid') and not partner.user_ids:
                partner.signup_prepare()

            route = 'login'
            # the parameters to encode for the query
            query = dict(db=self.env.cr.dbname)
            signup_type = self.env.context.get('signup_force_type_in_url', partner.signup_type or '')
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
                query['redirect'] = base + werkzeug.urls.url_encode(fragment)

            res[partner.id] = werkzeug.urls.url_join(base_url, "/web/%s?%s" % (route, werkzeug.urls.url_encode(query)))
        return res

    @api.multi
    def action_signup_prepare(self):
        return self.signup_prepare()

    def signup_get_auth_param(self):
        """ Get a signup token related to the partner if signup is enabled.
            If the partner already has a user, get the login parameter.
        """
        res = defaultdict(dict)

        allow_signup = self.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'true'
        for partner in self:
            if allow_signup and not partner.user_ids:
                partner.signup_prepare()
                res[partner.id]['auth_signup_token'] = partner.signup_token
            elif partner.user_ids:
                res[partner.id]['auth_login'] = partner.user_ids[0].login
        return res

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

    @api.model
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
                raise exceptions.UserError(_("Signup token '%s' is not valid") % token)
            return False
        if check_validity and not partner.signup_valid:
            if raise_exception:
                raise exceptions.UserError(_("Signup token '%s' is no longer valid") % token)
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
            res['email'] = res['login'] = partner.email or ''
        return res

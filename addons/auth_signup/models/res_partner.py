# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import werkzeug.urls

from collections import defaultdict
from datetime import datetime, timedelta

from odoo import api, exceptions, fields, models, tools, _

class SignupError(Exception):
    pass

def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.SystemRandom().choice(chars) for _ in range(20))

def now(**kwargs):
    return datetime.now() + timedelta(**kwargs)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signup_type = fields.Char(string='Signup Token Type', copy=False, groups="base.group_erp_manager")

    def _get_signup_url(self):
        self.ensure_one()
        result = self.sudo()._get_signup_url_for_action()
        if any(u._is_internal() for u in self.user_ids if u != self.env.user):
            self.env['res.users'].check_access('write')
        if any(u._is_portal() for u in self.user_ids if u != self.env.user):
            self.env['res.partner'].check_access('write')
        return result.get(self.id, False)

    def _get_signup_url_for_action(self, url=None, action=None, view_type=None, menu_id=None, res_id=None, model=None):
        """ generate a signup url for the given partner ids and action, possibly overriding
            the url state components (menu_id, id, view_type) """

        res = dict.fromkeys(self.ids, False)
        for partner in self:
            base_url = partner.get_base_url()
            # when required, make sure the partner has a valid signup token
            if self.env.context.get('signup_valid') and not partner.user_ids:
                partner.sudo().signup_prepare()

            route = 'login'
            # the parameters to encode for the query
            query = {'db': self.env.cr.dbname}
            if self.env.context.get('create_user'):
                query['signup_email'] = partner.email

            signup_type = self.env.context.get('signup_force_type_in_url', partner.sudo().signup_type or '')
            if signup_type:
                route = 'reset_password' if signup_type == 'reset' else signup_type

            query['token'] = partner.sudo()._generate_signup_token()

            if url:
                query['redirect'] = url
            else:
                fragment = dict()
                base = '/odoo/'
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

            signup_url = "/web/%s?%s" % (route, werkzeug.urls.url_encode(query))
            if not self.env.context.get('relative_url'):
                signup_url = tools.urls.urljoin(base_url, signup_url)
            res[partner.id] = signup_url
        return res

    def action_signup_prepare(self):
        return self.signup_prepare()

    def signup_get_auth_param(self):
        """ Get a signup token related to the partner if signup is enabled.
            If the partner already has a user, get the login parameter.
        """
        if not self.env.user._is_internal() and not self.env.is_admin():
            raise exceptions.AccessDenied()

        res = defaultdict(dict)

        allow_signup = self.env['res.users']._get_signup_invitation_scope() == 'b2c'
        for partner in self:
            partner = partner.sudo()
            if allow_signup and not partner.user_ids:
                partner.signup_prepare()
                res[partner.id]['auth_signup_token'] = partner._generate_signup_token()
            elif partner.user_ids:
                res[partner.id]['auth_login'] = partner.user_ids[0].login
        return res

    def signup_cancel(self):
        return self.write({'signup_type': None})

    def signup_prepare(self, signup_type="signup"):
        """ generate a new token for the partners with the given validity, if necessary """
        self.write({'signup_type': signup_type})
        return True

    @api.model
    def _signup_retrieve_partner(self, token, check_validity=False, raise_exception=False):
        """ find the partner corresponding to a token, and possibly check its validity

        :param token: the token to resolve
        :param bool check_validity: if True, also check validity
        :param bool raise_exception: if True, raise exception instead of returning False
        :return: partner (browse record) or False (if raise_exception is False)
        """
        partner = self._get_partner_from_token(token)
        if not partner:
            raise exceptions.UserError(_("Signup token '%s' is not valid or expired", token))
        return partner

    @api.model
    def _signup_retrieve_info(self, token):
        """ retrieve the user info about the token

        :rtype: dict | None
        :return: a dictionary with the user information if the token is valid,
            None otherwise:

                db
                    the name of the database
                token
                    the token, if token is valid
                name
                    the name of the partner, if token is valid
                login
                    the user login, if the user already exists
                email
                    the partner email, if the user does not exist
        """
        partner = self._get_partner_from_token(token)
        if not partner:
            return None
        res = {'db': self.env.cr.dbname}
        res['token'] = token
        res['name'] = partner.name
        if partner.user_ids:
            res['login'] = partner.user_ids[0].login
        else:
            res['email'] = res['login'] = partner.email or ''
        return res

    def _get_login_date(self):
        self.ensure_one()
        users_login_dates = self.user_ids.mapped('login_date')
        users_login_dates = list(filter(None, users_login_dates))  # remove falsy values
        if any(users_login_dates):
            return int(max(map(datetime.timestamp, users_login_dates)))
        return None

    def _generate_signup_token(self, expiration=None):
        """ Generate the signup token for the partner in self.

        Assume that :attr:`signup_type` is either ``'signup'`` or ``'reset'``.

        :param expiration: the time in hours before the expiration of the token
        :return: the signed payload/token that can be used to reset the
                 password/signup.

        Since ``last_login_date`` is part of the payload, this token is
        invalidated as soon as the user logs in.
        """
        self.ensure_one()
        if not expiration:
            if self.signup_type == 'reset':
                expiration = int(self.env['ir.config_parameter'].get_param("auth_signup.reset_password.validity.hours", 4))
            else:
                expiration = int(self.env['ir.config_parameter'].get_param("auth_signup.signup.validity.hours", 144))
        plist = [self.id, self.user_ids.ids, self._get_login_date(), self.signup_type]
        payload = tools.hash_sign(self.sudo().env, 'signup', plist, expiration_hours=expiration)
        return payload

    @api.model
    def _get_partner_from_token(self, token):
        if payload := tools.verify_hash_signed(self.sudo().env, 'signup', token):
            partner_id, user_ids, login_date, signup_type = payload
            # login_date can be either an int or "None" as a string for signup
            partner = self.browse(partner_id)
            if login_date == partner._get_login_date() and partner.user_ids.ids == user_ids and signup_type == partner.browse(partner_id).signup_type:
                return partner
        return None

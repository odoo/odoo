# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

import openerp
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval

import time
import random
import urlparse

def random_token():
    # the token has an entropy of about 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(chars) for i in xrange(20))

def now():
    return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


class res_partner(osv.Model):
    _inherit = 'res.partner'

    def _get_signup_valid(self, cr, uid, ids, name, arg, context=None):
        dt = now()
        res = {}
        for partner in self.browse(cr, uid, ids, context):
            res[partner.id] = bool(partner.signup_token) and (partner.signup_expiration or '') <= dt
        return res

    def _get_signup_url(self, cr, uid, ids, name, arg, context=None):
        """ determine a signup url for a given partner """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        template_url = '#action=login&db=%s&token=%s'

        # if required, make sure that every partner has a valid signup token
        if context and context.get('signup_valid'):
            self.signup_prepare(cr, uid, ids, context=context)

        res = dict.fromkeys(ids, False)
        for partner in self.browse(cr, uid, ids, context):
            if partner.signup_token:
                res[partner.id] = urlparse.urljoin(base_url, template_url % (cr.dbname, partner.signup_token))
        return res

    _columns = {
        'signup_token': fields.char(size=24, string='Signup Token'),
        'signup_expiration': fields.datetime(string='Signup Expiration'),
        'signup_valid': fields.function(_get_signup_valid, type='boolean', string='Signup Token is Valid'),
        'signup_url': fields.function(_get_signup_url, type='char', string='Signup URL'),
    }

    def action_signup_prepare(self, cr, uid, ids, context=None):
        return self.signup_prepare(cr, uid, ids, context=context)

    def signup_prepare(self, cr, uid, ids, expiration=False, context=None):
        """ generate a new token for the partners with the given validity, if necessary
            :param expiration: the expiration datetime of the token (string, optional)
        """
        for partner in self.browse(cr, uid, ids, context):
            if expiration or not partner.signup_valid:
                token = random_token()
                while self._signup_retrieve_partner(cr, uid, token, context=context):
                    token = random_token()
                partner.write({'signup_token': token, 'signup_expiration': expiration})
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
                raise Exception("Signup token '%s' is not valid" % token)
            return False
        partner = self.browse(cr, uid, partner_ids[0], context)
        if check_validity and not partner.signup_valid:
            if raise_exception:
                raise Exception("Signup token '%s' is no longer valid" % token)
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
            res['email'] = partner.email or ''
        return res



class res_users(osv.Model):
    _inherit = 'res.users'

    def signup(self, cr, uid, values, token=None, context=None):
        """ signup a user, to either:
            - create a new user (no token), or
            - create a user for a partner (with token, but no user for partner), or
            - change the password of a user (with token, and existing user).
            :param values: a dictionary with field values
            :param token: signup token (optional)
            :return: (dbname, login, password) for the signed up user
        """
        assert values.get('login') and values.get('password')
        result = (cr.dbname, values['login'], values['password'])

        if token:
            # signup with a token: find the corresponding partner id
            res_partner = self.pool.get('res.partner')
            partner = res_partner._signup_retrieve_partner(cr, uid, token,
                                        check_validity=True, raise_exception=True, context=None)
            # invalidate signup token
            partner.write({'signup_token': False, 'signup_expiration': False})
            if partner.user_ids:
                # user exists, modify its password
                partner.user_ids[0].write({'password': values['password']})
            else:
                # user does not exist: sign up invited user
                self._signup_create_user(cr, uid, {
                    'name': partner.name,
                    'login': values['login'],
                    'password': values['password'],
                    'email': values['login'],
                    'partner_id': partner.id,
                }, context=context)
            return result

        # sign up an external user
        assert values.get('name'), 'Signup: no name given for new user'
        self._signup_create_user(cr, uid, {
            'name': values['name'],
            'login': values['login'],
            'password': values['password'],
            'email': values['login'],
        }, context=context)
        return result

    def _signup_create_user(self, cr, uid, values, context=None):
        """ create a new user from the template user """
        ir_config_parameter = self.pool.get('ir.config_parameter')
        template_user_id = safe_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.template_user_id', 'False'))
        assert template_user_id and self.exists(cr, uid, template_user_id, context=context), 'Signup: invalid template user'

        # check that uninvited users may sign up
        if 'partner_id' not in values:
            if not safe_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.allow_uninvited', 'False')):
                raise Exception('Signup is not allowed for uninvited users')

        # create a copy of the template user (attached to a specific partner_id if given)
        values['active'] = True
        return self.copy(cr, uid, template_user_id, values, context=context)

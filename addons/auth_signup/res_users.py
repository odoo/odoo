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

import time
import random
import urlparse

def random_token():
    # the token has an entropy of 120 bits (6 bits/char * 20 chars)
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    return ''.join(random.choice(chars) for i in xrange(20))

def now():
    return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'signup_token': fields.char(size=24, string='Signup Ticket'),
        'signup_expiration': fields.datetime(string='Signup Expiration'),
    }

    def signup_generate_token(self, cr, uid, partner_id, context=None):
        """ generate a new token for a partner, and return it
            :param partner_id: the partner id
            :param expiration: the expiration datetime of the token (string, optional)
            :return: the token (string)
        """
        # generate a unique token
        token = random_token()
        while self.signup_retrieve_partner(cr, uid, token, context):
            token = random_token()
        self.write(cr, uid, [partner_id], {'signup_token': token, 'signup_expiration': expiration}, context=context)
        return token

    def signup_retrieve_partner(self, cr, uid, token, raise_exception=False, context=None):
        """ find the partner corresponding to a token, and return its partner id or False """
        partner_ids = self.search(cr, uid, [('signup_token', '=', token)], context=context)
        return partner_ids and partner_ids[0] or False

    def signup_get_url(self, cr, uid, partner_id, context):
        """ determine a url for the partner_id to sign up """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        token = self.browse(cr, uid, partner_id, context).signup_token
        if not token:
            token = self.signup_generate_token(cr, uid, partner_id, context=context)
        return urlparse.urljoin(base_url, '/login?db=%s#action=signup&token=%s' % (cr.dbname, token))

    def signup(self, cr, values, token=None, context=None):
        """ signup a user, to either:
            - create a new user (no token), or
            - create a user for a partner (with token, but no user for partner), or
            - change the password of a user (with token, and existing user).
            :param values: a dictionary with field values
            :param token: signup token (optional)
            :return: the uid of the signed up user
        """
        # signup the user, then log in (for setting properly the login_date)
        assert values.get('login') and values.get('password')
        uid = self._signup_user(cr, values, token, context)
        return self.login(cr.dbname, values['login'], values['password'])

    def _signup_user(self, cr, values, token=None, context=None):
        ir_config_parameter = self.pool.get('ir.config_parameter')
        values.update({'signup_token': False, 'signup_expiration': False})

        if token:
            # signup with a token: find the corresponding partner id
            partner_id = self.signup_retrieve_partner(cr, SUPERUSER_ID, token, context=None)
            if not partner_id:
                raise Exception('Signup token is not valid')
            partner = self.browse(cr, SUPERUSER_ID, partner_id, context)
            if partner.signup_expiration and partner.signup_expiration < now():
                raise Exception('Signup token is no longer valid')
            assert values['login'] == partner.email

            # if user exists, modify its password
            if partner.user_ids:
                user = partner.user_ids[0]
                user.write(values)
                return user.id

            # user does not exist: connect the new user to the partner
            values.update({'name': partner.name, 'partner_id': partner.id})

        else:
            # check whether uninvited users may sign up
            if not ir_config_parameter.get_param(cr, SUPERUSER_ID, 'auth_signup.allow_uninvited', False):
                raise Exception('Signup is not allowed for uninvited users')

        # create a new user
        assert values.get('name')
        values['email'] = values['login']
        template_user_id = ir_config_parameter.get_param(cr, SUPERUSER_ID, 'auth_signup.template_user_id')
        assert template_user_id, 'Signup: missing template user'
        return self.pool.get('res.users').copy(cr, SUPERUSER_ID, template_user_id, data, context=context)



class res_users(osv.Model):
    _inherit = 'res.users'

    def auth_signup_create(self, cr, uid, new_user, context=None):
        # new_user:
        #   login
        #   email
        #   name (optional)
        #   partner_id (optional)
        #   groups (optional)
        #   sign (for partner_id and groups)
        #
        user_template_id = self.pool.get('ir.config_parameter').get_param(cr, uid, 'auth_signup.template_user_id', 0)
        if user_template_id:
            self.pool.get('res.users').copy(cr, SUPERUSER_ID, user_template_id, new_user, context=context)
        else:
            self.pool.get('res.users').create(cr, SUPERUSER_ID, new_user, context=context)

    def auth_signup(self, cr, uid, name, login, password, context=None):
        r = (cr.dbname, login, password)
        res = self.search(cr, uid, [("login", "=", login)])
        if res:
            # Existing user
            user_id = res[0]
            try:
                self.check(cr.dbname, user_id, password)
                # Same password
            except openerp.exceptions.AccessDenied:
                # Different password
                raise
        else:
            # New user
            new_user = {
                'name': name,
                'login': login,
                'user_email': login,
                'password': password,
                'active': True,
            }
            self.auth_signup_create(cr, uid, new_user)
        return r

#

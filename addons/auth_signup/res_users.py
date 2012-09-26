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

    def signup_get_url(self, cr, uid, partner_ids, name, arg, context=None):
        """ determine a url for the partner_id to sign up """
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        res = {}
        for partner in self.browse(cr, uid, partner_ids, context):
            token = partner.signup_token
            if not token:
                token = self._signup_generate_token(cr, uid, partner.id, context=context)
            res[partner.id] = urlparse.urljoin(base_url, '#action=login&db=%s&token=%s' % (cr.dbname, token))
        return res

    _columns = {
        'signup_token': fields.char(size=24, string='Signup Ticket'),
        'signup_expiration': fields.datetime(string='Signup Expiration'),
        'signup_url': fields.function(signup_get_url, type='char', string='Signup URL'),
    }

    def _signup_generate_token(self, cr, uid, partner_id, expiration=False, context=None):
        """ generate a new token for a partner, and return it
            :param partner_id: the partner id
            :param expiration: the expiration datetime of the token (string, optional)
            :return: the token (string)
        """
        # generate a unique token
        token = random_token()
        while self._signup_retrieve_partner(cr, uid, token, context=context):
            token = random_token()
        self.write(cr, uid, [partner_id], {'signup_token': token, 'signup_expiration': expiration}, context=context)
        return token

    def _signup_retrieve_partner(self, cr, uid, token, raise_exception=False, context=None):
        """ find the partner corresponding to a token, and check its validity
            :return: partner (browse record) or False (if raise_exception is False)
            :raise: when token not valid (if raise_exception is True)
        """
        partner_ids = self.search(cr, uid, [('signup_token', '=', token)], context=context)
        if not partner_ids:
            if raise_exception:
                raise Exception("Signup token '%s' is not valid" % token)
            return False
        partner = self.browse(cr, uid, partner_ids[0], context)
        if partner.signup_expiration and partner.signup_expiration < now():
            if raise_exception:
                raise Exception("Signup token '%s' is no longer valid" % token)
            return False
        return partner

    def signup_retrieve_info(self, cr, uid, token, context=None):
        """ retrieve the user info about the token
            :return: either {'name': ..., 'login': ...} if a user exists for that token,
                     or {'name': ..., 'email': ...} otherwise
        """
        partner = self._signup_retrieve_partner(cr, uid, token, raise_exception=True, context=None)
        if partner.user_ids:
            return {'name': partner.name, 'login': partner.user_ids[0].login}
        else:
            return {'name': partner.name, 'email': partner.email or ''}



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
            partner = res_partner._signup_retrieve_partner(cr, uid, token, raise_exception=True, context=None)
            # invalidate signup token
            partner.write({'signup_token': False, 'signup_expiration': False})
            if partner.user_ids:
                # user exists, modify its password
                partner.user_ids[0].write({'password': values['password']})
            else:
                # user does not exist: sign up invited user
                self._signup_create_user(cr, uid, {
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

        values['active'] = True
        if values.get('partner_id'):
            # create a copy of the template user attached to values['partner_id']
            # note: we do not include 'partner_id' here, as copy() does not handle it correctly
            safe_values = {'login': values['login'], 'password': values['password']}
            user_id = self.copy(cr, uid, template_user_id, safe_values, context=context)
            # problem: the res.partner part of the template user has been duplicated
            # solution: unlink it, and replace it by values['partner_id']
            user = self.browse(cr, uid, user_id, context=context)
            partner = user.partner_id
            user.write(values)
            partner.unlink()
        else:
            # check that uninvited users may sign up
            if not safe_eval(ir_config_parameter.get_param(cr, uid, 'auth_signup.allow_uninvited', 'False')):
                raise Exception('Signup is not allowed for uninvited users')
            user_id = self.copy(cr, uid, template_user_id, values, context=context)

        return user_id

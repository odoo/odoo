# -*- coding: utf-8 -*-

import simplejson
import urllib2
import urlparse
import werkzeug.urls

import openerp
from openerp import api, fields, models
from openerp.addons.auth_signup.res_users import SignupError


class ResUsers(models.Model):
    _inherit = 'res.users'

    oauth_provider_id = fields.Many2one(
        'auth.oauth.provider', string='OAuth Provider')
    oauth_uid = fields.Char(
        string='OAuth User ID', help="Oauth Provider user_id", copy=False)
    oauth_access_token = fields.Char(
        string='OAuth Access Token', readonly=True, copy=False)

    _sql_constraints = [
        ('uniq_users_oauth_provider_oauth_uid', 'unique(oauth_provider_id, oauth_uid)',
         'OAuth UID must be unique per provider'),
    ]

    def _auth_oauth_rpc(self, endpoint, access_token):
        params = werkzeug.url_encode({'access_token': access_token})
        if urlparse.urlparse(endpoint)[4]:
            url = endpoint + '&' + params
        else:
            url = endpoint + '?' + params
        f = urllib2.urlopen(url)
        response = f.read()
        return simplejson.loads(response)

    def _auth_oauth_validate(self, provider, access_token):
        """ return the validation data corresponding to the access token """
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        validation = self._auth_oauth_rpc(
            oauth_provider.validation_endpoint, access_token)
        if validation.get("error"):
            raise Exception(validation['error'])
        if oauth_provider.data_endpoint:
            data = self._auth_oauth_rpc(
                oauth_provider.data_endpoint, access_token)
            validation.update(data)
        return validation

    def _auth_oauth_signin(self, provider, validation, params):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: openerp.exceptions.AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        try:
            oauth_uid = validation['user_id']
            oauth_users = self.search(
                [("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
            if not oauth_users:
                raise openerp.exceptions.AccessDenied()
            assert len(oauth_users) == 1
            oauth_users.write({'oauth_access_token': params['access_token']})
            return oauth_users.login
        except openerp.exceptions.AccessDenied, access_denied_exception:
            if self.env.context.get('no_user_creation'):
                return None
            state = simplejson.loads(params['state'])
            token = state.get('t')
            oauth_uid = validation['user_id']
            email = validation.get(
                'email', 'provider_%s_user_%s' % (provider, oauth_uid))
            name = validation.get('name', email)
            values = {
                'name': name,
                'login': email,
                'email': email,
                'oauth_provider_id': provider,
                'oauth_uid': oauth_uid,
                'oauth_access_token': params['access_token'],
                'active': True,
            }
            try:
                _, login, _ = self.signup(values, token)
                return login
            except SignupError:
                raise access_denied_exception

    @api.model
    def auth_oauth(self, provider, params):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        access_token = params.get('access_token')
        validation = self._auth_oauth_validate(provider, access_token)
        # required check
        if not validation.get('user_id'):
            raise openerp.exceptions.AccessDenied()
        # retrieve and sign in user
        login = self._auth_oauth_signin(provider, validation, params)
        if not login:
            raise openerp.exceptions.AccessDenied()
        # return user credentials
        return (self.env.cr.dbname, login, access_token)

    @api.model
    def check_credentials(self, password):
        try:
            return super(ResUsers, self).check_credentials(password)
        except openerp.exceptions.AccessDenied:
            res = self.sudo().search(
                [('id', '=', self.env.uid), ('oauth_access_token', '=', password)])
            if not res:
                raise

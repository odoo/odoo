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
import logging

import openerp
import openerp.addons.web.controllers.main as webmain
from openerp.addons.auth_signup.res_users import SignupError
from openerp import http
from openerp.http import request, LazyResponse
from openerp.tools.translate import _
from openerp.tools import exception_to_unicode

_logger = logging.getLogger(__name__)

class AuthSignup(openerp.addons.web.controllers.main.Home):

    @http.route()
    def web_login(self, *args, **kw):
        mode = request.params.get('mode')
        qcontext = request.params.copy()
        super_response = None
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            return http.redirect_with_hash(request.params.get('redirect'))
        if request.httprequest.method != 'POST' or mode not in ('reset', 'signup'):
            # Default behavior is to try to login,  which in reset or signup mode in a non-sense.
            super_response = super(AuthSignup, self).web_login(*args, **kw)
        response = webmain.render_bootstrap_template(request.session.db, 'auth_signup.signup', qcontext, lazy=True)
        if isinstance(super_response, LazyResponse):
            response.params['values'].update(super_response.params['values'])
        token = qcontext.get('token', None)
        token_infos = None
        if token:
            try:
                # retrieve the user info (name, login or email) corresponding to a signup token
                res_partner = request.registry.get('res.partner')
                token_infos = res_partner.signup_retrieve_info(request.cr, openerp.SUPERUSER_ID, token)
                for k, v in token_infos.items():
                    qcontext.setdefault(k, v)
            except:
                qcontext['error'] = _("Invalid signup token")
                response.params['template'] = 'web.login'
                return response

        # retrieve the module config (which features are enabled) for the login page
        icp = request.registry.get('ir.config_parameter')
        config = {
            'signup': icp.get_param(request.cr, openerp.SUPERUSER_ID, 'auth_signup.allow_uninvited') == 'True',
            'reset': icp.get_param(request.cr, openerp.SUPERUSER_ID, 'auth_signup.reset_password') == 'True',
        }
        qcontext.update(config)

        if 'error' in request.params or mode not in ('reset', 'signup') or (not token and not config[mode]):
            if isinstance(super_response, LazyResponse):
                super_response.params['values'].update(config)
            return super_response

        if request.httprequest.method == 'GET':
            if token_infos:
                qcontext.update(token_infos)
        else:
            res_users = request.registry.get('res.users')
            login = request.params.get('login')
            if mode == 'reset' and not token:
                try:
                    res_users.reset_password(request.cr, openerp.SUPERUSER_ID, login)
                    qcontext['message'] = _("An email has been sent with credentials to reset your password")
                    response.params['template'] = 'web.login'
                except Exception, e:
                    qcontext['error'] = exception_to_unicode(e) or _("Could not reset your password")
                    _logger.exception('error when resetting password')
            else:
                values = dict((key, qcontext.get(key)) for key in ('login', 'name', 'password'))
                try:
                    self._signup_with_values(token, values)
                    redirect = request.params.get('redirect')
                    if not redirect:
                        redirect = '/web?' + request.httprequest.query_string
                    return http.redirect_with_hash(redirect)
                except SignupError, e:
                    qcontext['error'] = exception_to_unicode(e)

        return response

    def _signup_with_values(self, token, values):
        db, login, password = request.registry['res.users'].signup(request.cr, openerp.SUPERUSER_ID, values, token)
        request.cr.commit()     # as authenticate will use its own cursor we need to commit the current transaction
        uid = request.session.authenticate(db, login, password)
        if not uid:
            raise SignupError(_('Authentification Failed.'))


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:

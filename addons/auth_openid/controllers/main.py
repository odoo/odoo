# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
import os
import tempfile
import getpass

import werkzeug.urls
import werkzeug.exceptions

from openid import oidutil
from openid.store import filestore
from openid.consumer import consumer
from openid.cryptutil import randomString
from openid.extensions import ax, sreg

import openerp
from openerp import SUPERUSER_ID
from openerp.modules.registry import RegistryManager
from openerp.addons.web.controllers.main import login_and_redirect, set_cookie_and_redirect
import openerp.http as http
from openerp.http import request

from .. import utils

_logger = logging.getLogger(__name__)
oidutil.log = _logger.debug

def get_system_user():
    """Return system user info string, such as USERNAME-EUID"""
    try:
        info = getpass.getuser()
    except ImportError:
        if os.name == 'nt':
            # when there is no 'USERNAME' in environment, getpass.getuser()
            # fail when trying to import 'pwd' module - which is unix only.
            # In that case we have to fallback to real win32 API.
            import win32api
            info = win32api.GetUserName()
        else:
            raise

    euid = getattr(os, 'geteuid', None) # Non available on some platforms
    if euid is not None:
        info = '%s-%d' % (info, euid())
    return info

_storedir = os.path.join(tempfile.gettempdir(), 
                         'openerp-auth_openid-%s-store' % get_system_user())

class GoogleAppsAwareConsumer(consumer.GenericConsumer):
    def complete(self, message, endpoint, return_to):
        if message.getOpenIDNamespace() == consumer.OPENID2_NS:
            server_url = message.getArg(consumer.OPENID2_NS, 'op_endpoint', '')
            if server_url.startswith('https://www.google.com/a/'):
                assoc_handle = message.getArg(consumer.OPENID_NS, 'assoc_handle')
                assoc = self.store.getAssociation(server_url, assoc_handle)
                if assoc:
                    # update fields
                    for attr in ['claimed_id', 'identity']:
                        value = message.getArg(consumer.OPENID2_NS, attr, '')
                        value = 'https://www.google.com/accounts/o8/user-xrds?uri=%s' % werkzeug.url_quote_plus(value)
                        message.setArg(consumer.OPENID2_NS, attr, value)

                    # now, resign the message
                    message.delArg(consumer.OPENID2_NS, 'sig')
                    message.delArg(consumer.OPENID2_NS, 'signed')
                    message = assoc.signMessage(message)

        return super(GoogleAppsAwareConsumer, self).complete(message, endpoint, return_to)


class OpenIDController(http.Controller):

    _store = filestore.FileOpenIDStore(_storedir)

    _REQUIRED_ATTRIBUTES = ['email']
    _OPTIONAL_ATTRIBUTES = 'nickname fullname postcode country language timezone'.split()

    def _add_extensions(self, oidrequest):
        """Add extensions to the oidrequest"""

        sreg_request = sreg.SRegRequest(required=self._REQUIRED_ATTRIBUTES,
                                        optional=self._OPTIONAL_ATTRIBUTES)
        oidrequest.addExtension(sreg_request)

        ax_request = ax.FetchRequest()
        for alias in self._REQUIRED_ATTRIBUTES:
            uri = utils.SREG2AX[alias]
            ax_request.add(ax.AttrInfo(uri, required=True, alias=alias))
        for alias in self._OPTIONAL_ATTRIBUTES:
            uri = utils.SREG2AX[alias]
            ax_request.add(ax.AttrInfo(uri, required=False, alias=alias))

        oidrequest.addExtension(ax_request)

    def _get_attributes_from_success_response(self, success_response):
        attrs = {}

        all_attrs = self._REQUIRED_ATTRIBUTES + self._OPTIONAL_ATTRIBUTES

        sreg_resp = sreg.SRegResponse.fromSuccessResponse(success_response)
        if sreg_resp:
            for attr in all_attrs:
                value = sreg_resp.get(attr)
                if value is not None:
                    attrs[attr] = value

        ax_resp = ax.FetchResponse.fromSuccessResponse(success_response)
        if ax_resp:
            for attr in all_attrs:
                value = ax_resp.getSingle(utils.SREG2AX[attr])
                if value is not None:
                    attrs[attr] = value
        return attrs

    def _get_realm(self):
        return request.httprequest.host_url

    @http.route('/auth_openid/login/verify_direct', type='http', auth='none')
    def verify_direct(self, db, url):
        result = self._verify(db, url)
        if 'error' in result:
            return werkzeug.exceptions.BadRequest(result['error'])
        if result['action'] == 'redirect':
            return werkzeug.utils.redirect(result['value'])
        return result['value']

    @http.route('/auth_openid/login/verify', type='json', auth='none')
    def verify(self, db, url):
        return self._verify(db, url)

    def _verify(self, db, url):
        redirect_to = werkzeug.urls.Href(request.httprequest.host_url + 'auth_openid/login/process')(session_id=request.session_id)
        realm = self._get_realm()

        session = dict(dbname=db, openid_url=url)       # TODO add origin page ?
        oidconsumer = consumer.Consumer(session, self._store)

        try:
            oidrequest = oidconsumer.begin(url)
        except consumer.DiscoveryFailure, exc:
            fetch_error_string = 'Error in discovery: %s' % (str(exc[0]),)
            return {'error': fetch_error_string, 'title': 'OpenID Error'}

        if oidrequest is None:
            return {'error': 'No OpenID services found', 'title': 'OpenID Error'}

        request.session.openid_session = session
        self._add_extensions(oidrequest)

        if oidrequest.shouldSendRedirect():
            redirect_url = oidrequest.redirectURL(realm, redirect_to)
            return {'action': 'redirect', 'value': redirect_url, 'session_id': request.session_id}
        else:
            form_html = oidrequest.htmlMarkup(realm, redirect_to)
            return {'action': 'post', 'value': form_html, 'session_id': request.session_id}

    @http.route('/auth_openid/login/process', type='http', auth='none')
    def process(self, **kw):
        session = getattr(request.session, 'openid_session', None)
        if not session:
            return set_cookie_and_redirect('/')

        oidconsumer = consumer.Consumer(session, self._store, consumer_class=GoogleAppsAwareConsumer)

        query = request.httprequest.args
        info = oidconsumer.complete(query, request.httprequest.base_url)
        display_identifier = info.getDisplayIdentifier()

        session['status'] = info.status

        if info.status == consumer.SUCCESS:
            dbname = session['dbname']
            registry = RegistryManager.get(dbname)
            with registry.cursor() as cr:
                Modules = registry.get('ir.module.module')

                installed = Modules.search_count(cr, SUPERUSER_ID, ['&', ('name', '=', 'auth_openid'), ('state', '=', 'installed')]) == 1
                if installed:

                    Users = registry.get('res.users')

                    #openid_url = info.endpoint.canonicalID or display_identifier
                    openid_url = session['openid_url']

                    attrs = self._get_attributes_from_success_response(info)
                    attrs['openid_url'] = openid_url
                    session['attributes'] = attrs
                    openid_email = attrs.get('email', False)

                    domain = []
                    if openid_email:
                        domain += ['|', ('openid_email', '=', False)]
                    domain += [('openid_email', '=', openid_email)]

                    domain += [('openid_url', '=', openid_url), ('active', '=', True)]

                    ids = Users.search(cr, SUPERUSER_ID, domain)
                    assert len(ids) < 2
                    if ids:
                        user_id = ids[0]
                        login = Users.browse(cr, SUPERUSER_ID, user_id).login
                        key = randomString(utils.KEY_LENGTH, '0123456789abcdef')
                        Users.write(cr, SUPERUSER_ID, [user_id], {'openid_key': key})
                        # TODO fill empty fields with the ones from sreg/ax
                        cr.commit()

                        return login_and_redirect(dbname, login, key)

            session['message'] = 'This OpenID identifier is not associated to any active users'

        elif info.status == consumer.SETUP_NEEDED:
            session['message'] = info.setup_url
        elif info.status == consumer.FAILURE and display_identifier:
            fmt = "Verification of %s failed: %s"
            session['message'] = fmt % (display_identifier, info.message)
        else:   # FAILURE
            # Either we don't understand the code or there is no
            # openid_url included with the error. Give a generic
            # failure message. The library should supply debug
            # information in a log.
            session['message'] = 'Verification failed.'

        return set_cookie_and_redirect('/#action=login&loginerror=1')

    @http.route('/auth_openid/login/status', type='json', auth='none')
    def status(self):
        session = getattr(request.session, 'openid_session', {})
        return {'status': session.get('status'), 'message': session.get('message')}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

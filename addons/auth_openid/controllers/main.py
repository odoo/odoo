# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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
import sys
import urllib

import werkzeug.urls
import werkzeug.exceptions

from openerp.modules.registry import RegistryManager
import web.common.http as openerpweb

from openid import oidutil
from openid.store import memstore
#from openid.store import filestore
from openid.consumer import consumer
from openid.cryptutil import randomString
from openid.extensions import ax, sreg

from .. import utils



_logger = logging.getLogger('web.auth_openid')
oidutil.log = logging.getLogger('openid').debug


class GoogleAppsAwareConsumer(consumer.GenericConsumer):
    def complete(self, message, endpoint, return_to):
        if message.getOpenIDNamespace() == consumer.OPENID2_NS:
            server_url = message.getArg(consumer.OPENID2_NS, 'op_endpoint', consumer.no_default)
            if server_url.startswith('https://www.google.com/a/'):
                # update fields
                for attr in ['claimed_id', 'identity']:
                    value = message.getArg(consumer.OPENID2_NS, attr)
                    value = 'https://www.google.com/accounts/o8/user-xrds?uri=%s' % urllib.quote_plus(value)
                    message.setArg(consumer.OPENID2_NS, attr, value)

                # now, resign the message
                assoc_handle = message.getArg(consumer.OPENID_NS, 'assoc_handle')
                assoc = self.store.getAssociation(server_url, assoc_handle)
                message.delArg(consumer.OPENID2_NS, 'sig')
                message.delArg(consumer.OPENID2_NS, 'signed')
                message = assoc.signMessage(message)

        return super(GoogleAppsAwareConsumer, self).complete(message, endpoint, return_to) 


class OpenIDController(openerpweb.Controller):
    _cp_path = '/auth_openid/login'

    _store = memstore.MemoryStore()  # TODO use a filestore

    _REQUIRED_ATTRIBUTES = ['email']
    _OPTIONAL_ATTRIBUTES = 'nickname fullname postcode country language timezone'.split()


    def _add_extensions(self, request):
        """Add extensions to the request"""

        sreg_request = sreg.SRegRequest(required=self._REQUIRED_ATTRIBUTES,
                                        optional=self._OPTIONAL_ATTRIBUTES)
        request.addExtension(sreg_request)

        ax_request = ax.FetchRequest()
        for alias in self._REQUIRED_ATTRIBUTES:
            uri = utils.SREG2AX[alias]
            ax_request.add(ax.AttrInfo(uri, required=True, alias=alias))
        for alias in self._OPTIONAL_ATTRIBUTES:
            uri = utils.SREG2AX[alias]
            ax_request.add(ax.AttrInfo(uri, required=False, alias=alias))

        request.addExtension(ax_request)

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

    def _get_realm(self, req):
        return req.httprequest.host_url

    @openerpweb.jsonrequest
    def verify(self, req, db, url):
        redirect_to = werkzeug.urls.Href(req.httprequest.host_url + 'auth_openid/login/process')(session_id=req.session_id)
        realm = self._get_realm(req)

        session = dict(dbname=db, openid_url=url)       # TODO add origin page ?
        oidconsumer = consumer.Consumer(session, self._store)

        try:
            request = oidconsumer.begin(url)
        except consumer.DiscoveryFailure, exc:
            fetch_error_string = 'Error in discovery: %s' % (str(exc[0]),)
            return {'error': fetch_error_string, 'title': 'OpenID Error'}

        if request is None:
            return {'error': 'No OpenID services found', 'title': 'OpenID Error'}

        req.session.openid_session = session
        self._add_extensions(request)

        if request.shouldSendRedirect():
            redirect_url = request.redirectURL(realm, redirect_to)
            return {'action': 'redirect', 'value': redirect_url, 'session_id': req.session_id}
        else:
            form_html = request.htmlMarkup(realm, redirect_to)
            return {'action': 'post', 'value': form_html, 'session_id': req.session_id}

    
    @openerpweb.httprequest
    def process(self, req, **kw):
        session = getattr(req.session, 'openid_session', None)
        if not session:
            return werkzeug.utils.redirect('/')

        oidconsumer = consumer.Consumer(session, self._store, consumer_class=GoogleAppsAwareConsumer)

        query = req.httprequest.args
        info = oidconsumer.complete(query, req.httprequest.base_url)
        display_identifier = info.getDisplayIdentifier()

        session['status'] = info.status
        user_id = None

        if info.status == consumer.SUCCESS:
            dbname = session['dbname']
            with utils.cursor(dbname) as cr:
                registry = RegistryManager.get(dbname)
                Modules = registry.get('ir.module.module')

                installed = Modules.search_count(cr, 1, ['&', ('name', '=', 'auth_openid'), ('state', '=', 'installed')]) == 1
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

                    domain += [
                               ('openid_url', '=', openid_url),
                               ('active', '=', True),
                              ]
                    ids = Users.search(cr, 1, domain)
                    assert len(ids) < 2
                    if ids:
                        user_id = ids[0]
                        login = Users.browse(cr, 1, user_id).login
                        key = randomString(utils.KEY_LENGTH, '0123456789abcdef')
                        Users.write(cr, 1, [user_id], {'openid_key': key})
                        # TODO fill empty fields with the ones from sreg/ax
                        cr.commit()

                        u = req.session.login(dbname, login, key)

            if not user_id:
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


        fragment = '#loginerror' if not user_id else ''
        return werkzeug.utils.redirect('/web/webclient/home?debug=1'+fragment)

    @openerpweb.jsonrequest
    def status(self, req):
        session = getattr(req.session, 'openid_session', {})
        return {'status': session.get('status'), 'message': session.get('message')}


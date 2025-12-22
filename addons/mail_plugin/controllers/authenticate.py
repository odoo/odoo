# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import hmac
import json
import logging
import odoo
import werkzeug

from odoo import _, http
from odoo.http import request
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)


class Authenticate(http.Controller):

    @http.route(['/mail_client_extension/auth', '/mail_plugin/auth'], type='http', auth="user", methods=['GET'], website=True)
    def auth(self, **values):
        """
         Once authenticated this route renders the view that shows an app wants to access Odoo.
         The user is invited to allow or deny the app. The form posts to `/mail_client_extension/auth/confirm`.

         old route name "/mail_client_extension/auth is deprecated as of saas-14.3,it is not needed for newer
         versions of the mail plugin but necessary for supporting older versions
         """
        if not request.env.user._is_internal():
            return request.render('mail_plugin.app_error', {'error': _('Access Error: Only Internal Users can link their inboxes to this database.')})
        return request.render('mail_plugin.app_auth', values)

    @http.route(['/mail_client_extension/auth/confirm', '/mail_plugin/auth/confirm'], type='http', auth="user", methods=['POST'])
    def auth_confirm(self, scope, friendlyname, redirect, info=None, do=None, **kw):
        """
        Called by the `app_auth` template. If the user decided to allow the app to access Odoo, a temporary auth code
        is generated and they are redirected to `redirect` with this code in the URL. It should redirect to the app, and
        the app should then exchange this auth code for an access token by calling
        `/mail_client/auth/access_token`.

        old route name "/mail_client_extension/auth/confirm is deprecated as of saas-14.3,it is not needed for newer
        versions of the mail plugin but necessary for supporting older versions
        """
        parsed_redirect = werkzeug.urls.url_parse(redirect)
        params = parsed_redirect.decode_query()
        if do:
            name = friendlyname if not info else f'{friendlyname}: {info}'
            auth_code = self._generate_auth_code(scope, name)
            # params is a MultiDict which does not support .update() with kwargs
            # the state attribute is needed for the gmail connector
            params.update({'success': 1, 'auth_code': auth_code, 'state': kw.get('state', '')})
        else:
            params.update({'success': 0, 'state': kw.get('state', '')})
        updated_redirect = parsed_redirect.replace(query=werkzeug.urls.url_encode(params))
        return request.redirect(updated_redirect.to_url(), local=False)

    @http.route(['/mail_plugin/auth/check_version'], type='json', auth="none", cors="*",
                methods=['POST', 'OPTIONS'])
    def auth_check_version(self):
        """Allow to know if the module is installed and which addin version is supported."""
        return 1

    # In this case, an exception will be thrown in case of preflight request if only POST is allowed.
    @http.route(['/mail_client_extension/auth/access_token', '/mail_plugin/auth/access_token'], type='json', auth="none", cors="*",
                methods=['POST', 'OPTIONS'])
    def auth_access_token(self, auth_code='', **kw):
        """
        Called by the external app to exchange an auth code, which is temporary and was passed in a URL, for an
        access token, which is permanent, and can be used in the `Authorization` header to authorize subsequent requests

        old route name "/mail_client_extension/auth/access_token is deprecated as of saas-14.3,it is not needed for newer
        versions of the mail plugin but necessary for supporting older versions
        """
        if not auth_code:
            return {"error": "Invalid code"}
        auth_message = self._get_auth_code_data(auth_code)
        if not auth_message:
            return {"error": "Invalid code"}
        request.update_env(user=auth_message['uid'])
        scope = 'odoo.plugin.' + auth_message.get('scope', '')
        api_key = request.env['res.users.apikeys']._generate(
            scope,
            auth_message['name'],
            datetime.datetime.now() + datetime.timedelta(days=1)
        )
        return {'access_token': api_key}

    def _get_auth_code_data(self, auth_code):
        data, auth_code_signature = auth_code.split('.')
        data = base64.b64decode(data)
        auth_code_signature = base64.b64decode(auth_code_signature)
        signature = odoo.tools.misc.hmac(request.env(su=True), 'mail_plugin', data).encode()
        if not hmac.compare_digest(auth_code_signature, signature):
            return None

        auth_message = json.loads(data)
        # Check the expiration
        if datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(auth_message['timestamp']) > datetime.timedelta(
                minutes=3):
            return None

        return auth_message

    # Using UTC explicitly in case of a distributed system where the generation and the signature verification do not
    # necessarily happen on the same server
    def _generate_auth_code(self, scope, name):
        if not request.env.user._is_internal():
            raise NotFound()
        auth_dict = {
            'scope': scope,
            'name': name,
            'timestamp': int(datetime.datetime.utcnow().timestamp()),
            # <- elapsed time should be < 3 mins when verifying
            'uid': request.uid,
        }
        auth_message = json.dumps(auth_dict, sort_keys=True).encode()
        signature = odoo.tools.misc.hmac(request.env(su=True), 'mail_plugin', auth_message).encode()
        auth_code = "%s.%s" % (base64.b64encode(auth_message).decode(), base64.b64encode(signature).decode())
        _logger.info('Auth code created - user %s, scope %s', request.env.user, scope)
        return auth_code

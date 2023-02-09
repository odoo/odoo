# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class GoogleGmailController(http.Controller):
    @http.route('/google_gmail/confirm', type='http', auth='user')
    def google_gmail_callback(self, code=None, state=None, error=None, **kwargs):
        """Callback URL during the OAuth process.

        Gmail redirects the user browser to this endpoint with the authorization code.
        We will fetch the refresh token and the access token thanks to this authorization
        code and save those values on the given mail server.
        """
        if not request.env.user.has_group('base.group_system'):
            _logger.error('Google Gmail: non-system user trying to link an Gmail account.')
            raise Forbidden()

        if error:
            return _('An error occur during the authentication process.')

        try:
            state = json.loads(state)
            model_name = state['model']
            rec_id = state['id']
            csrf_token = state['csrf_token']
            email = state['email']
        except Exception:
            _logger.error('Google Gmail: Wrong state value %r.', state)
            raise Forbidden()

        record = self._get_gmail_record(model_name, rec_id, csrf_token)

        GmailToken = request.env['google.gmail.token']

        try:
            refresh_token, access_token, expiration = GmailToken._fetch_gmail_refresh_token(code)
        except UserError:
            return _('An error occur during the authentication process.')

        return self._redirect_to_gmail_record(email, access_token, expiration, refresh_token, record)

    @http.route('/google_gmail/iap_confirm', type='http', auth='user')
    def google_gmail_iap_callback(self, model, rec_id, email, csrf_token, access_token, refresh_token, expiration, **kwargs):
        record = self._get_gmail_record(model, rec_id, csrf_token)
        return self._redirect_to_gmail_record(email, access_token, expiration, refresh_token, record)

    def _get_gmail_record(self, model_name, rec_id, csrf_token):
        """Return the record after checking the CSRF token."""
        model = request.env[model_name]

        if not isinstance(model, request.env.registry['google.gmail.mixin']):
            # The model must inherits from the "google.gmail.mixin" mixin
            _logger.error('Error during Gmail OAuth process, wrong model %r.', model_name)
            raise Forbidden()

        record = model.browse(int(rec_id)).exists()
        if not record:
            _logger.error('Error during Gmail OAuth process, record does not exist %r #%r.', model_name, rec_id)
            raise Forbidden()

        if not csrf_token or not consteq(csrf_token, record._get_gmail_csrf_token()):
            _logger.error('Google Gmail: Wrong CSRF token during Gmail authentication.')
            raise Forbidden()

        return record

    def _redirect_to_gmail_record(self, email, access_token, expiration, refresh_token, record):
        # update existing token or create a new one
        request.env['google.gmail.token']._search_or_create(email, {
            'google_gmail_access_token': access_token,
            'google_gmail_access_token_expiration': expiration,
            'google_gmail_refresh_token': refresh_token,
        })

        # redirect to the record form view
        return request.redirect(f'/odoo/{record._name}/{record.id}')

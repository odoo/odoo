# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MicrosoftOutlookController(http.Controller):
    @http.route('/microsoft_outlook/confirm', type='http', auth='user')
    def microsoft_outlook_callback(self, code=None, state=None, error_description=None, **kwargs):
        """Callback URL during the OAuth process.

        Outlook redirects the user browser to this endpoint with the authorization code.
        We will fetch the refresh token and the access token thanks to this authorization
        code and save those values on the given mail server.
        """
        if error_description:
            _logger.warning("Microsoft Outlook: an error occurred %s", error_description)
            return request.render('microsoft_outlook.microsoft_outlook_oauth_error', {
                'error': error_description,
                'redirect_url': '/odoo',
            })

        try:
            state = json.loads(state)
            model_name = state['model']
            rec_id = state['id']
            csrf_token = state['csrf_token']
        except Exception:
            _logger.error('Microsoft Outlook: Wrong state value %r.', state)
            raise Forbidden()

        record_sudo = self._get_outlook_record(model_name, rec_id, csrf_token)

        try:
            refresh_token, access_token, expiration = record_sudo._fetch_outlook_refresh_token(code)
        except UserError as e:
            return request.render('microsoft_outlook.microsoft_outlook_oauth_error', {
                'error': str(e),
                'redirect_url': self._get_redirect_url(record_sudo),
            })

        return self._check_email_and_redirect_to_outlook_record(access_token, expiration, refresh_token, record_sudo)

    def _get_outlook_record(self, model_name, rec_id, csrf_token):
        """Return the given record after checking the CSRF token."""
        model = request.env[model_name]

        if not isinstance(model, request.env.registry['microsoft.outlook.mixin']):
            # The model must inherits from the "microsoft.outlook.mixin" mixin
            _logger.error('Microsoft Outlook: Wrong model %r.', model_name)
            raise Forbidden()

        record = model.browse(int(rec_id)).exists().sudo()
        if not record:
            _logger.error('Microsoft Outlook: Record not found.')
            raise Forbidden()

        if not csrf_token or not consteq(csrf_token, record._get_outlook_csrf_token()):
            _logger.error('Microsoft Outlook: Wrong CSRF token during Outlook authentication.')
            raise Forbidden()

        return record

    def _check_email_and_redirect_to_outlook_record(self, access_token, expiration, refresh_token, record):
        # Verify the token information (that the email set on the
        # server is the email used to login on Outlook)
        if (record._name == 'ir.mail_server' and (record.owner_user_id or not request.env.user.has_group('base.group_system'))):
            response = requests.get(
                "https://outlook.office.com/api/v2.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=5,
            )
            if not response.ok:
                _logger.error('Microsoft Outlook: Could not verify the token information: %s.', response.text)
                raise Forbidden()

            response = response.json()
            if response.get('EmailAddress') != record[record._email_field]:
                _logger.error('Microsoft Outlook: Invalid email address: %r != %s.', response, record[record._email_field])
                return request.render('microsoft_outlook.microsoft_outlook_oauth_error', {
                    'error': _(
                        "Oops, you're creating an authorization to send from %(email_login)s but your address is %(email_server)s. Make sure your addresses match!",
                        email_login=response.get('EmailAddress'),
                        email_server=record[record._email_field],
                    ),
                    'redirect_url': self._get_redirect_url(record),
                })

        record.write({
            'active': True,
            'microsoft_outlook_refresh_token': refresh_token,
            'microsoft_outlook_access_token': access_token,
            'microsoft_outlook_access_token_expiration': expiration,
        })
        return request.redirect(self._get_redirect_url(record))

    def _get_redirect_url(self, record):
        """Return the redirect URL for the given record.

        If the user configured a personal mail server, we redirect him
        to the user preference view. If it's an admin and that he
        configured a standard incoming / outgoing mail server, then we
        redirect it to the mail server form view.
        """
        if (
            (record._name != 'ir.mail_server'
            or record != request.env.user.outgoing_mail_server_id)
            and request.env.user.has_group('base.group_system')
        ):
            return f'/odoo/{record._name}/{record.id}'
        return f'/odoo/my-preferences/{request.env.user.id}'

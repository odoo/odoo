# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import werkzeug

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class MicrosoftOutlookController(http.Controller):
    @http.route('/microsoft_outlook/callback', type='http', auth='user')
    def microsoft_outlook_callback(self, code=None, state=None, error_description=None):
        """Callback URL during the OAuth process.

        Outlook redirects the user browser to this endpoint with the authorization code.
        We will fetch the refresh token and the access token thanks to this authorization
        code and save those values on the given mail server.
        """
        if not request.env.user.has_group('base.group_system'):
            raise NotFound()

        try:
            state = json.loads(state)
            model_name = state['model']
            rec_id = state['id']
            csrf_token = state['csrf_token']
        except Exception:
            raise NotFound()

        if error_description:
            return request.render('microsoft_outlook.microsoft_outlook_oauth_error', {
                'error': error_description,
                'model_name': model_name,
                'rec_id': rec_id,
            })

        model = request.env[model_name]

        if 'microsoft.outlook.mixin' not in model._inherit:
            # The model must inherits from the "microsoft.outlook.mixin" mixin
            raise NotFound()

        record = model.browse(rec_id).exists()
        if not record or not csrf_token or not consteq(csrf_token, record._get_outlook_csrf_token()):
            raise NotFound()

        try:
            refresh_token, access_token, expiration = record._fetch_refresh_token(code)
        except UserError as e:
            # TODO: use custom Exception
            return request.render('microsoft_outlook.microsoft_outlook_oauth_error', {
                'error': str(e.name),
                'model_name': model_name,
                'rec_id': rec_id,
            })

        record.write({
            'microsoft_outlook_refresh_token': refresh_token,
            'microsoft_outlook_access_token': access_token,
            'microsoft_outlook_access_token_expiration': expiration,
        })

        # TODO: show toast message to confirm that the server has been connected
        return werkzeug.utils.redirect(f'/web?#id={rec_id}&model={model_name}&view_type=form', 303)

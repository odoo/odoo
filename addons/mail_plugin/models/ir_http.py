# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from werkzeug.exceptions import Unauthorized
from werkzeug.datastructures import WWWAuthenticate

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_outlook(cls):
        access_token = request.httprequest.headers.get('Authorization')
        if not access_token:
            raise Unauthorized('Access token missing', www_authenticate=WWWAuthenticate('bearer'))

        if access_token.startswith('Bearer '):
            access_token = access_token[7:]

        user_id = request.env["res.users.apikeys"]._check_credentials(scope='odoo.plugin.outlook', key=access_token)
        if not user_id:
            raise Unauthorized('Access token invalid', www_authenticate=WWWAuthenticate('bearer'))

        # take the identity of the API key user
        request.update_env(user=user_id)

        # switch to the user context
        request.update_context(**request.env.user.context_get())

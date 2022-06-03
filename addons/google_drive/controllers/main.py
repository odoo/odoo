# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http
from odoo.http import request

from werkzeug.exceptions import Forbidden
from werkzeug.urls import url_encode

import logging
import werkzeug

_logger = logging.getLogger(__name__)


class GoogleDriveController(http.Controller):
    @http.route(['/google_drive/confirm'], type='http', auth='user')
    def google_drive_confirm(self, code=None, state=None, error=None, **kwargs):
        if not request.env.is_admin():
            _logger.error('Google Drive: Access Denied to non-system user on /google_drive/confirm')
            raise Forbidden()

        if error:
            return _('An error occurred during the setup of Google Drive: %s', error)

        refresh_token = request.env['google.drive.config']._request_token('authorization_code', code=code)
        request.env['ir.config_parameter'].sudo().set_param('google_drive_refresh_token', refresh_token['refresh_token'])

        settings_menu = request.env.ref('base.menu_administration')
        return werkzeug.utils.redirect('/web#%s' % url_encode({'menu_id': settings_menu.id}))

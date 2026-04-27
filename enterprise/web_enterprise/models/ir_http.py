# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import models
from odoo.http import request
from odoo.tools import html_sanitize

_logger = logging.getLogger(__name__)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _post_logout(cls):
        super()._post_logout()
        request.future_response.set_cookie('color_scheme', max_age=0)

    def webclient_rendering_context(self):
        """ Overrides community to prevent unnecessary load_menus request """
        return {
            'session_info': self.session_info(),
        }

    def session_info(self):
        ICP = self.env['ir.config_parameter'].sudo()

        if self.env.user.has_group('base.group_system'):
            warn_enterprise = 'admin'
        elif self.env.user._is_internal():
            warn_enterprise = 'user'
        else:
            warn_enterprise = False

        result = super(Http, self).session_info()
        result['support_url'] = "https://www.odoo.com/help"
        if warn_enterprise:
            result['warning'] = warn_enterprise
            result['expiration_date'] = ICP.get_param('database.expiration_date')
            result['expiration_reason'] = ICP.get_param('database.expiration_reason')
            if ICP.get_param('sysadmin.message'):
                try:
                    sysadmin_message = json.loads(ICP.get_param('sysadmin.message'))
                    if 'message' in sysadmin_message:
                        sysadmin_message['message'] = html_sanitize(sysadmin_message['message'], sanitize_tags=False)
                    result['sysadmin_message'] = sysadmin_message
                except Exception:
                    _logger.exception('Failed to load sysadmin.message in ir.config_parameter')
        return result

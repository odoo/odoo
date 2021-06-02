# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hmac
from hashlib import sha256

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()

        if self.env.user.has_group('base.group_user'):
            icp = request.env['ir.config_parameter'].sudo()
            db_uuid = icp.get_param('database.uuid')
            db_secret = icp.get_param('database.secret')
            message = db_uuid + str(request.uid)
            token = hmac.new(message.encode('utf-8'), db_secret.encode('utf-8'), sha256).hexdigest()

            result['db_uuid'] = db_uuid
            result['support_token'] = token
            result['support_origin'] = False  # must be overridden to specify the correct origin

        return result

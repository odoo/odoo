# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OdooByAdyenController(http.Controller):
    _notification_url = '/payment/odoo_adyen/notification'

    @http.route('/payment/odoo_adyen/notification', type='json', auth='public', csrf=False)
    def odoo_adyen_notification(self):
        data = json.loads(request.httprequest.data)
        _logger.info('Beginning Odoo by Adyen form_feedback with data %s', pprint.pformat(data)) 
        if data.get('authResult') not in ['CANCELLED']:
            request.env['payment.transaction'].sudo().form_feedback(data, 'odoo_adyen')

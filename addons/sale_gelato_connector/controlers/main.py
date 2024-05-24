
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint
import logging
import requests
import json
from odoo.http import request
from odoo import http


_logger = logging.getLogger(__name__)


class StripeController(http.Controller):
    _webhook_url = '/gelato/webhook'

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def stripe_webhook(self):
        event = request.get_json_data()
        _logger.info("Notification received from Gelato with data:\n%s", pprint.pformat(event))

        # compare keys
        #which webhooks we might need:
            # ship tracking

        #if webhook event tracking code, then send a message to chatter and maybe on email with
        '''
            Status that would interest us:
            created,uploading,passed,in_production,printed,draft,failed(and why), canceled, digitizing(maybe),
            on_hold(maybe), shipped,
        '''
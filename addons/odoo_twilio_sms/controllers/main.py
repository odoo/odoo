from odoo import http
from odoo.http import request
from twilio.twiml.messaging_response import MessagingResponse
import logging

_logger = logging.getLogger(__name__)


class TwilioWebhookController(http.Controller):

    @http.route("/sms", type='http', auth='public', methods=['GET', 'POST'], cors="*", csrf=False)
    def sms_reply(self, **kwargs):
        try:
            resp = MessagingResponse()
            resp.message("Thank you for contacting!")
            response_text = str(resp)
            _logger.info("Twilio SMS response sent successfully.", resp)
            return request.make_response(response_text, headers=[('Content-Type', 'text/xml')])
        except Exception as e:
            _logger.error("Error in Twilio webhook processing: %s", str(e), exc_info=True)
            return request.make_response(
                "<Response><Message>Error processing request</Message></Response>",
                headers=[('Content-Type', 'text/xml')],
                status=500
            )

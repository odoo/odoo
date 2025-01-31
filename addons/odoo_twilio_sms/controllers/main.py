from odoo import http, _
from odoo.http import request
from twilio.twiml.messaging_response import MessagingResponse
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class TwilioWebhookController(http.Controller):

    @http.route("/sms", type='http', auth='public', methods=['GET', 'POST'], cors="*", csrf=False)
    def sms_reply(self, **kwargs):
        try:
            resp = MessagingResponse()
            #TODO: Change it later on because below code is done as per assumptions of twilio response
            """
            resp = {
                'from_number': '+919999999999'
                'message_body': 'xyz'
                'reply_message_id': 1234
            }
            """
            if resp:
                self._process_sms(resp)
            _logger.info("Twilio SMS response sent successfully.", resp)
            return request.make_response(str(resp), headers=[('Content-Type', 'text/xml')])
        except Exception as e:
            _logger.error("Error in Twilio webhook processing: %s", str(e), exc_info=True)
            return request.make_response(
                "<Response><Message>Error processing request</Message></Response>",
                headers=[('Content-Type', 'text/xml')],
                status=500
            )

    def _process_sms(self, resp):
        """
        Process incoming SMS and determine reply
        Override this method to customize response logic
        """
        try:
            if resp['reply_message_id']:
                log_id = request.env['twilio.message.log'].sudo().search([('messaging_service_sid', '=', resp['reply_message_id'])], limit=1)
                if log_id and log_id.res_model and log_id.res_id:
                    active_id = request.env[log_id.res_model].sudo().browse(int(log_id.res_id))
                    if active_id:
                        _logger.info("SMS received successfully via Twilio with SID: %s", resp['reply_message_id'])
                        active_id.message_post(
                            body=f"SMS received from {resp['from_number']}: {resp['message_body']}",
                            message_type="notification",
                            subtype_xmlid="mail.mt_note",
                        )
                        msg_dict = {
                            "account_sid": log_id.account_sid,
                            "body": resp['message_body'],
                            "date_sent": datetime.now(),
                            "from_phone": resp['from_number'],
                            "messaging_service_sid": resp['messaging_service_sid'],
                            "sid": resp['sid'],
                            "status": "received",
                            "to_phone": log_id.from_phone,
                            "res_model": log_id.res_model,
                            "res_id": log_id.res_id,
                            "is_reply_message": True,
                            "res_name": active_id.name,
                            "user_id": active_id.user_id and active_id.user_id.id or False,
                            "company_id": active_id.company_id and active_id.company_id.id or False,
                        }
                        log_message = request.env['twilio.message.log'].sudo().create(msg_dict)
            else:
                # Example: Look up partner by phone number
                Partner = request.env['res.partner'].sudo()
                partner_id = Partner.search([('mobile', 'ilike', resp['from_number'])], limit=1)
                if partner_id:
                    _logger.info("SMS received successfully via Twilio with SID: %s", resp['reply_message_id'])
                    partner_id.message_post(
                        body=f"SMS received from {resp['from_number']}: {resp['message_body']}",
                        message_type="notification",
                        subtype_xmlid="mail.mt_note",
                    )
                    msg_dict = {
                        "account_sid": resp.account_sid,
                        "body": resp['message_body'],
                        "date_sent": datetime.now(),
                        "from_phone": resp['from_number'],
                        "messaging_service_sid": resp.messaging_service_sid,
                        "sid": resp.sid,
                        "status": "received",
                        "to_phone": resp.from_phone,
                        "res_model": 'res.partner',
                        "res_id": partner_id.id,
                        "res_name": partner_id.name,
                        "user_id": partner_id.user_id and partner_id.user_id.id or False,
                        "company_id": partner_id.company_id and partner_id.company_id.id or False,
                    }
                    log_message = request.env['twilio.message.log'].sudo().create(msg_dict)
        except Exception as e:
            _logger.error(f'Error processing SMS: {str(e)}')
            return "Sorry, we couldn't process your request. Please try again later."

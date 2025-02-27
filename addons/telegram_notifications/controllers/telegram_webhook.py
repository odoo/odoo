from odoo import http
import json

class TelegramWebhookController(http.Controller):

    @http.route('/telegram/webhook/receiver', type='json', auth='public', methods=['POST'], csrf=False)
    def handle_webhook(self, **post):
        payload = json.loads(http.request.httprequest.data)
        if 'message' in payload:
            chat_id = payload['message']['chat']['id']
            message_text = payload['message']['text']
            bot = http.request.env['telegram.bot'].search([], limit=1)
            if bot:
                bot.send_telegram_message(chat_id, "Thank you for contacting us!")
        return {"status": "ok"}
from odoo import http
from odoo.http import request

class ChatbotController(http.Controller):

    @http.route('/chatbot', type='http', auth='public', website=True)
    def chatbot_page(self, **kwargs):
        return request.render('a_bot.chatbot_template')

    @http.route('/chatbot/send_message', type='json', auth='public')
    def send_message(self, message):
        chatbot_model = request.env['chatbot.model'].sudo().search([], limit=1)
        if chatbot_model:
            response = chatbot_model.send_message(message)
            return {'response': response}
        return {'response': 'No chatbot configuration found'}
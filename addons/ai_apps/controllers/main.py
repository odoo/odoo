from odoo import _, http
from odoo.http import request
from odoo.exceptions import AccessError
from markupsafe import Markup

class HTML_Editor(http.Controller):
    @http.route(["/ai_apps/generate_w_composer"], type="jsonrpc", auth="user")
    def generate_text(self, prompt, channel_id):
        try:
            composer_channel = request.env['discuss.channel'].browse(channel_id)
            # remove HTML tags from the prompt (LLMs get confused and format their replies using HTML)
            prompt = Markup(prompt).striptags()
            # generate response by sending prompt to the chatgpt api
            response = composer_channel.submit_to_model(prompt, composer_channel.ai_context)
            # add original prompt to the conversation history (context)
            composer_channel.add_message_to_context(prompt, 'user')
            print(composer_channel.ai_context)
            # post response as odoobot
            composer_channel.create_response(response)
        except AccessError:
            raise AccessError(_("Oops, it looks like our AI is unreachable!"))

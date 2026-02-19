from odoo import models, _
from odoo.exceptions import UserError
import requests


class CommunicationChannel(models.Model):
    _inherit = 'mail.channel'

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super(CommunicationChannel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        chatgpt_channel_id = self.env.ref('hia_chatgpt_integration.channel_chatgpt')
        user_chatgpt = self.env.ref("hia_chatgpt_integration.user_chatgpt")
        partner_chatgpt = self.env.ref("hia_chatgpt_integration.partner_chatgpt")
        author_id = msg_vals.get('author_id')
        chatgpt_name = str(partner_chatgpt.name or '') + ', '
        prompt = msg_vals.get('body')
        if not prompt:
            return rdata
        Partner = self.env['res.partner']
        partner_name = ''
        if author_id:
            partner_id = Partner.browse(author_id)
            if partner_id:
                partner_name = partner_id.name

        if self.channel_type == 'chat':
            if (author_id != partner_chatgpt.id and
                    (chatgpt_name in msg_vals.get('record_name', '') or 'ChatGPT,' in msg_vals.get('record_name', ''))):
                try:
                    res = self._get_chatgpt_response(prompt=prompt)
                    self.with_user(user_chatgpt).message_post(body=res, message_type='comment', subtype_xmlid='mail.mt_comment')
                except Exception as e:
                    raise UserError(_(e))

        elif msg_vals.get('model', '') == 'mail.channel' and msg_vals.get('res_id', 0) == chatgpt_channel_id.id:
            if author_id != partner_chatgpt.id:
                try:
                    res = self._get_chatgpt_response(prompt=prompt)
                    chatgpt_channel_id.with_user(user_chatgpt).message_post(body=res, message_type='comment', subtype_xmlid='mail.mt_comment')
                except Exception as e:
                    raise UserError(_(e))
        return rdata
    
    def _get_chatgpt_response(self, prompt):
        # Replace with the actual ChatGPT endpoint URL
        chatgpt_url = "https://api.openai.com/v1/chat/completions"

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('hia_chatgpt_integration.openapi_api_key')

        tempreture_id = ICP.get_param('hia_chatgpt_integration.tempreture_id')
        tempreture = self.env['chatgpt.tempreture'].browse(int(tempreture_id)).name

        gpt_model_id = ICP.get_param('hia_chatgpt_integration.chatgp_model')
        gpt_model = 'gpt-3.5-turbo'
        try:
            if gpt_model_id:
                gpt_model = self.env['chatgpt.model'].browse(int(gpt_model_id)).name
        except Exception as ex:
            gpt_model = 'gpt-3.5-turbo'
            pass

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"  # Include authentication based on API requirements
        }

        body = {
            "model": gpt_model,  # Replace with the desired model (if applicable)
            "messages": [
                {"role": "system", "content": prompt}
            ],
            "temperature": float(tempreture),  # Adjust temperature for desired response style
        }

        try:
            response = requests.post(chatgpt_url, headers=headers, json=body)
            response.raise_for_status()  # Raise an exception for non-2xx status codes

            # Parse the response (assuming JSON format based on OpenAI API)
            data = response.json()
            chatgpt_response = data["choices"][0]["message"]["content"]
            return chatgpt_response

        except requests.exceptions.RequestException as e:
            return "Please enter valid OPEN AI Api key."
        except Exception as e:  # Catch other potential exceptions
            return e
            
from odoo import models, _

import io
import base64
import logging
import requests
from PIL import Image
from markupsafe import Markup

_logger = logging.getLogger(__name__)

GEMINI_MODELS = {
    'gemini_pro': 'gemini-pro',
    'gemini_pro_vision': 'gemini-pro-vision',
    'gemini_1_5_pro': 'gemini-1-5-pro',
    'gemini_1_5_flash': 'gemini-1-5-flash'
}

class DiscussChannel(models.Model):
    _inherit = 'mail.channel'

    def _notify_thread(self, message, msg_vals=None, **kwargs):
        rdata = super(DiscussChannel, self)._notify_thread(
            message, msg_vals=msg_vals, **kwargs)

        prompt = msg_vals.get('body')
        attachments = msg_vals.get('attachment_ids')
        if not prompt and len(attachments) == 0:
            return rdata

        gemini_channel_id = self.env.ref(
            'hia_gemini_ai_integration.channel_gemini')
        user_gemini = self.env.ref("hia_gemini_ai_integration.user_gemini")
        partner_gemini = self.env.ref(
            "hia_gemini_ai_integration.partner_gemini")
        author_id = msg_vals.get('author_id')
        gemini_name = str(partner_gemini.name or '') + ', '

        self.env.cr.commit()
        
        try:
            attached_images_ids = []
            for attachment_tuple in attachments:
                attachment_id = attachment_tuple[1]
                if self.image_attachment(attachment_id):
                    attached_images_ids.append(attachment_id)
            if (
                author_id != partner_gemini.id
                and (
                    gemini_name in msg_vals.get('record_name', '')
                    or 'Gemini,' in msg_vals.get('record_name', '')
                )
                and self.channel_type == 'chat'):
                response_text = self._gemini_ai_response(
                    prompt=prompt, attached_images_ids=attached_images_ids)
                response_text_markup = Markup(_(response_text))
                self.with_user(user_gemini).message_post(
                    body=response_text_markup,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )   
            elif (
                author_id != partner_gemini.id
                and msg_vals.get('model', '') == 'mail.channel'
                and msg_vals.get('res_id', 0) == gemini_channel_id.id
            ):
                response_text = self._gemini_ai_response(
                    prompt=prompt, attached_images_ids=attached_images_ids)
                response_text_markup = Markup(_(response_text))
                gemini_channel_id.with_user(user_gemini).message_post(
                    body=response_text_markup,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
        except Exception as e:
            _logger.error(e)
            return str(e)

        return rdata

    def image_attachment(self, attachment_id):
        attachment = self.env['ir.attachment'].browse(attachment_id)
        data = base64.b64decode(attachment.datas)

        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
                return True
        except (IOError, SyntaxError) as e:
            return False

    def _gemini_ai_response(self, prompt, attached_images_ids=[]):
        config_parameter = self.env['ir.config_parameter'].sudo()
        gemini_api_key = config_parameter.get_param(
            'hia_gemini_ai_integration.gemini_api_key')
        gemini_model_id = config_parameter.get_param(
            'hia_gemini_ai_integration.gemini_model')
        prompt_template = f"""
        You are a helpful assistant.
        Here is the user's question:{prompt}
        Formulate a response as HTML text. Use HTML tags like <br> and <b> to format the text. Here is an example:
        <p>Your schedule for today, June 11, 2024:</p><br/>
        <ul>
            <li><b>09:00 AM - 10:00 AM:</b> Team meeting in Conference Room A</li>
            <li><b>11:00 AM - 11:30 AM:</b> Client call with Virtual Reality Systems</li>
            <li><b>02:00 PM - 03:00 PM:</b> Project review meeting with the development team</li>
            <li><b>04:00 PM - 05:00 PM:</b> Development sprint planning session in Room B</li>
        </ul>
        <br/>
        <p>Is there anything else I can help you with?</p>
        Now, use your knowledge to answer the user's question.
        """

        prompt = prompt_template
        if not gemini_api_key:
            return "Please provide the Gemini API key (follow: Settings > Gemini > Gemini API Key)"

        try:
            if gemini_model_id:
                gemini_model = self.env['gemini.model'].browse(
                    int(gemini_model_id)).name
        except Exception as e:
            gemini_model = GEMINI_MODELS['gemini_pro']
            _logger.error(e)
        
        if gemini_model == 'gemini-pro' and attached_images_ids:
            return "Please change the model; 'gemini-pro' does not support images."
        elif gemini_model == 'gemini-pro-vision' and not attached_images_ids:
            return "The 'gemini-pro-vision' model expects both text and images."

        try:
            base_url = f"https://generativelanguage.googleapis.com"
            endpoint = f'/v1/models/{gemini_model}:generateContent?key={gemini_api_key}'

            _logger.debug(f"Using Gemini API endpoint: {base_url}{endpoint}")
            headers = {
                "Content-Type": "application/json"
            }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ]
            }

            if attached_images_ids:
                for attachment_id in attached_images_ids:
                    attachment = self.env['ir.attachment'].browse(attachment_id)
                    data = base64.b64decode(attachment.datas)
                    image_data = io.BytesIO(data).read()
                    part = {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64.b64encode(image_data).decode('utf-8')
                        }
                    }
                    payload["contents"][0]["parts"].append(part)

            response = requests.post(
                base_url + endpoint,
                headers=headers,
                json=payload)

            if response.status_code == 200:
                response_data = response.json()
                return response_data['candidates'][0]['content']['parts'][0]['text']
            else:
                return _("Error from Gemini API: %s") % response.text
        except Exception as e:
            _logger.error(e)
            return str(e)
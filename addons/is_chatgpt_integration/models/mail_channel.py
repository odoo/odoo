# -*- coding: utf-8 -*-
# Copyright (c) 2020-Present InTechual Solutions. (<https://intechualsolutions.com/>)

from openai import OpenAI

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Channel(models.Model):
    _inherit = 'mail.channel'

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super(Channel, self)._notify_thread(message, msg_vals=msg_vals, **kwargs)
        chatgpt_channel_id = self.env.ref('is_chatgpt_integration.channel_chatgpt')
        user_chatgpt = self.env.ref("is_chatgpt_integration.user_chatgpt")
        partner_chatgpt = self.env.ref("is_chatgpt_integration.partner_chatgpt")
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
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('is_chatgpt_integration.openapi_api_key')
        client = OpenAI(api_key=api_key)
        gpt_model_id = ICP.get_param('is_chatgpt_integration.chatgp_model')
        gpt_model = 'text-davinci-003'
        try:
            if gpt_model_id:
                gpt_model = self.env['chatgpt.model'].browse(int(gpt_model_id)).name
        except Exception as ex:
            gpt_model = 'text-davinci-003'
            pass
        try:
            response = client.chat.completions.create(
                messages=[{"role": "system", "content": prompt}],
                model=gpt_model,
                temperature=0.6,
                max_tokens=3000,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                user=self.env.user.name
            )
            res = response.choices[0].message.content
            return res
        except Exception as e:
            raise UserError(_(e))

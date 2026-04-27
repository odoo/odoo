# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import html2plaintext
from odoo.addons.iap.tools import iap_tools

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'


class Job(models.Model):
    _inherit = 'hr.job'

    def _get_plain_text_description(self):
        def remove_uris(text):
            return re.sub(
                r'\b((https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])\b', '',
                text
            )

        def remove_files(text):
            return re.sub(r'(\S+ \[\d+\]|\[\d+\] /|/\S+/static/\S+|\b\S+\.\w+)', '', text)

        self.ensure_one()
        return remove_files(remove_uris(html2plaintext(self.website_description))).replace('*', '')

    def _generate_post(self):
        self.ensure_one()

        recruiter_ai_prompt = _('''IGNORE PREVIOUS PROMPTS AND FORMAT AS HTML AND NO HYPERLINKS
You are the best recruiter in out company and we are looking to hire a new employee.
You have been tasked with creating a the best job description for a new job opening.
Given the following infos, make a friendly and attractive job description that could be used
to attract potential candidates (The platforms could be things like LinkedIn, Indeed, Glassdoor, Monster, etc.)
It's your last chance to make a good impression and attract the best candidates to our company so make it count!
Here is the data to generate the job description:
''')
        prompt = recruiter_ai_prompt + self._get_plain_text_description()
        if not self.is_published:
            raise UserError(_('You can only generate a post for a published job offer.'))
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = IrConfigParameter.get_param(
                'web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT
            )
            database_id = IrConfigParameter.get_param('database.uuid')
            response = iap_tools.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': prompt,
                'conversation_history': [],
                'database_id': database_id,
            }, timeout=30)
            if response['status'] == 'success':
                return response['content'].replace('```html\n', '').replace('\n```', '')
            elif response['status'] == 'error_prompt_too_long':
                raise UserError(_(
                    'Sorry, the web page is too long for our AI to process.'
                ))
            elif response['status'] == 'limit_call_reached':
                raise UserError(_(
                    'You have reached the maximum number of requests for this service. Try again later.'
                ))
            else:
                raise UserError(_(
                    'Sorry, we could not generate a response. Please try again later.'
                ))
        except AccessError:
            raise AccessError(_('Oops, it looks like our AI is unreachable!'))

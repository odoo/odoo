# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models, _
from odoo.exceptions import UserError, AccessError
from odoo.addons.iap.tools import iap_tools

sub_tags = re.compile(r'<[^>]*>').sub
section_regex = re.compile(
    r'<section[^>]*class="([^"]*)"[^>]*>(.*?)</section>',
    re.DOTALL
)
paragraph_regex = re.compile(
    r'<p[^>]*>(.*?)</p>',
    re.DOTALL
)
rating_regex = re.compile(
    r'\s*<h6(?: class="[^"]*")?>(.*?)</h6>'
    r'\s*<div(?: class="[^"]*")?[^>]*>\s*'
    r'<span(?: class="[^"]*")?[^>]*>\s*((?:<i(?: class="[^"]*")?[^>]*></i>\s*)*)</span>'
    r'\s*<span(?: class="[^"]*")?[^>]*>\s*((?:<i(?: class="[^"]*")?[^>]*></i>\s*)*)</span>'
    r'\s*</div>',
    re.DOTALL
)
box_regex = re.compile(
    r'<div(?: class="[^"]*")?[^>]*>\s*'
    r'<h[1-6](?: class="[^"]*")?>(.*?)</h[1-6]>\s*'
    r'(?:<br>\s*)?'
    r'<ul(?: class="[^"]*")?[^>]*>\s*'
    r'((?:<li(?: class="[^"]*")?[^>]*>.*?</li>\s*)+)</ul>\s*'
    r'</div>',
    re.DOTALL
)
close_i_tag = re.compile(r'</i>')
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
AI_BASE_PROMPT = """
Given the following infos, Generate a professional job description that could be used to attract potential candidates:
The platforms could be things like LinkedIn, Indeed, Glassdoor, Monster, etc.
"""

class Job(models.Model):
    _inherit = 'hr.job'

    def action_extract_data(self):
        self.ensure_one()
        related_webpage = self.website_description
        url = self.full_url
        sections = section_regex.findall(related_webpage)
        post_text = 'job title: ' + self.name + '\njob url: ' + url + '\n\n'

        for class_name, section in sections:
            if 'image' in class_name:
                continue
            elif 'comparisons' in class_name:
                boxes = box_regex.findall(section)
                for title, content in boxes:
                    post_text += '\n' + title + ':\n'
                    content = content.split('\n')
                    for item in content:
                        post_text += sub_tags('', item) + '\n'
            elif 'features' in class_name:
                post_text += sub_tags('', section)
            else:
                ratings = rating_regex.findall(section)
                post_text += 'job features: \n'
                for rating in ratings:
                    active_icons = len(close_i_tag.findall(rating[1]))
                    inactive_icons = len(close_i_tag.findall(rating[2]))
                    infos = rating[0] + ' ' + str(active_icons) + '/' + str(inactive_icons + active_icons) + '\n'
                    post_text += infos
                paragraph_text = paragraph_regex.findall(section)
                post_text += '\njob description: \n'
                for paragraph in paragraph_text:
                    paragraph = re.sub('\n +', ' ', paragraph)
                    post_text += sub_tags('', paragraph) + '\n'
        return re.sub('\n\n+', '\n\n', re.sub('\n+ +', '\n', re.sub(' +', ' ', post_text)))

    def generate_post(self):
        self.ensure_one()
        prompt = AI_BASE_PROMPT + self.action_extract_data()
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = IrConfigParameter.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            database_id = IrConfigParameter.get_param('database.uuid')
            response = iap_tools.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': prompt,
                'conversation_history': [],
                'database_id': database_id,
            }, timeout=30)
            if response['status'] == 'success':
                return response['content']
            elif response['status'] == 'error_prompt_too_long':
                raise UserError(_("Sorry, your prompt is too long. Try to say it in fewer words."))
            elif response['status'] == 'limit_call_reached':
                raise UserError(_("You have reached the maximum number of requests for this service. Try again later."))
            else:
                raise UserError(_("Sorry, we could not generate a response. Please try again later."))
        except AccessError:
            raise AccessError(_("Oops, it looks like our AI is unreachable!"))

    def action_generate_post(self):
        self.ensure_one()
        self.write({'description': self.generate_post().replace('\n', '<br/>')})

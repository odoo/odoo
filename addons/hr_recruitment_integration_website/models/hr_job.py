# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models

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

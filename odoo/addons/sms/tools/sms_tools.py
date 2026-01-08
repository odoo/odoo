# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

import markupsafe

from odoo.tools import TEXT_URL_REGEX, create_link, html_escape


def sms_content_to_rendered_html(text):
    """Transforms plaintext into html making urls clickable and preserving newlines"""
    urls = re.findall(TEXT_URL_REGEX, text)
    escaped_text = html_escape(text)
    for url in urls:
        escaped_text = escaped_text.replace(url, markupsafe.Markup(create_link(url, url)))
    return markupsafe.Markup(re.sub(r'\r?\n|\r', '<br/>', escaped_text))

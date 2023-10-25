# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tools import html_escape, html_keep_url


def sms_content_to_rendered_html(text):
    """Transforms plaintext into html making urls clickable and preserving newlines"""
    text_with_links = html_keep_url(str(html_escape(text)))
    return re.sub(r'\r?\n|\r', '<br/>', text_with_links)

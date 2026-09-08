import re

import markupsafe

from odoo.tools import html_escape
from odoo.tools.mail import TEXT_URL_REGEX, create_link


def sms_content_to_rendered_html(text):
    """Transforms plaintext into html making urls clickable and preserving newlines"""
    parts = []
    last_end = 0
    for match in TEXT_URL_REGEX.finditer(text):
        url = match.group(0)
        parts.append(html_escape(text[last_end : match.start()]))
        parts.append(markupsafe.Markup(create_link(url, url)))
        last_end = match.end()
    parts.append(html_escape(text[last_end:]))
    escaped_text = "".join(parts)
    return markupsafe.Markup(re.sub(r"\r?\n|\r", "<br/>", escaped_text))

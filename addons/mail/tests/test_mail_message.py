# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo.tests.common import TransactionCase

HTML_MSG_BODY_NO_STYLE = \
"""<pre style="white-space:pre-wrap">*Hello*

*World*</pre>"""
HTML_MSG_BODY_NO_QUOTE_WITH_STYLE = """
<p>
    <span class="some_useless_style_that_takes_too_much_space"><strong>Hello</strong></span>
    <br>
    <span class="some_useless_style_that_takes_too_much_space"><strong>World</strong></span>
</p>
"""
HTML_MSG_BODY_ONE_QUOTE_WITH_STYLE = """
<p>
    <span class="some_useless_style_that_takes_too_much_space"><strong>Hello</strong></span>
    <br>
    <span class="some_useless_style_that_takes_too_much_space"><strong>World</strong></span>
    <blockquote data-o-mail-quote="1">
        Some reply text
    </blockquote>
</p>
"""
HTML_MSG_BODY_NESTED_QUOTES_WITH_STYLE = """
<p>
    <span class="some_useless_style_that_takes_too_much_space"><strong>Hello</strong></span>
    <br>
    <span class="some_useless_style_that_takes_too_much_space"><strong>World</strong></span>
    <blockquote data-o-mail-quote="1">
        Some reply text
        <blockquote data-o-mail-quote="1">
            Another reply
        </blockquote>
    </blockquote>
</p>
"""
HTML_MSG_BODY_MULTI_NESTED_QUOTES_WITH_STYLE = """
<p>
    <span class="some_useless_style_that_takes_too_much_space"><strong>Hello</strong></span>
    <br>
    <span class="some_useless_style_that_takes_too_much_space"><strong>World</strong></span>
    <blockquote data-o-mail-quote="1">
        Some reply text
        <blockquote data-o-mail-quote="1">
            Another reply
            <blockquote data-o-mail-quote="1">
                Yet another reply
            </blockquote>
        </blockquote>
    </blockquote>
</p>
"""

HTML_BODY_TEMPLATES = [
    HTML_MSG_BODY_NO_QUOTE_WITH_STYLE,
    HTML_MSG_BODY_ONE_QUOTE_WITH_STYLE,
    HTML_MSG_BODY_NESTED_QUOTES_WITH_STYLE,
    HTML_MSG_BODY_MULTI_NESTED_QUOTES_WITH_STYLE,
]

class TestMailMessage(TransactionCase):

    def test_compress_message_body(self):
        some_partner = self.env.ref('base.res_partner_1')
        messages = self.env['mail.message'].create([
            {
                'body': template,
                'partner_ids': [(4, some_partner.id)],
                'message_type': 'email',
            }
            for template in HTML_BODY_TEMPLATES
        ])
        self.env['ir.config_parameter'].sudo().set_param('mail_message.last_compressed_id', str(min(messages.ids) - 1))
        messages._cron_compress_messages()
        for message in messages:
            self.assertEqual(message.body, Markup(HTML_MSG_BODY_NO_STYLE))
        self.assertEqual(int(self.env['ir.config_parameter'].sudo().get_param('mail_message.last_compressed_id')), max(messages.ids))

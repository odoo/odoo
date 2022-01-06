# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.addons.base.tests import test_mail_examples
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('mail_server')
class TestIrMailServer(TransactionCase):

    def test_mail_body(self):
        bodies = [
            'content',
            '<p>content</p>',
            '<head><meta content="text/html; charset=utf-8" http-equiv="Content-Type"></head><body><p>content</p></body>',
            test_mail_examples.MISC_HTML_SOURCE,
            test_mail_examples.QUOTE_THUNDERBIRD_HTML,
        ]
        expected_list = [
            'content',
            'content',
            'content',
            "test1\n\n**test2**\n\n_test3_\n\n_test4_\n\n~~test5~~\n\ntest6\n\n  * test7\n  * test8\n\n  1. test9\n  2. test10\n\n> test11\n\n> > test12\n>>\n\n>>  \n>\n\n[google](http://google.com) [test link](javascript:alert\('malicious code'\))",
            'On 01/05/2016 10:24 AM, Raoul Poilvache wrote:  \n\n> **_Test reply. The suite._**  \n>\n>\n>  \n>\n>\n> \--  \n>\n>\n> Raoul Poilvache\n\nTop cool !!!  \n  \n\n    \n    \n    -- \n    Raoul Poilvache\n    ',
        ]
        for body, expected in zip(bodies, expected_list):
            message = self.env['ir.mail_server'].build_email(
                'john.doe@from.example.com',
                'destinataire@to.example.com',
                body=body,
                subject='Subject',
                subtype='html',
            )
            body_alternative = False
            for part in message.walk():
                if part.get_content_type() == 'text/plain':
                    body_alternative = tools.ustr(part.get_payload(decode=True))
                    # remove ending new lines as it just adds noise
                    body_alternative = body_alternative.strip('\n')
            self.assertEqual(body_alternative, expected)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo.tests.common import TransactionCase
from odoo.addons.mail.tests.common import MailCommon
from odoo.modules.module import get_module_resource

class TestDigestMail(TransactionCase, MailCommon):

    def test_digest_image_base64(self):
        """ Check that local images' src are replaced with their
        respective base64 data src
        """
        digest = self.env['digest.digest'].create({
            'name': 'test digest mail',
            'user_ids': [(6)],
        })

        image_local_link = '/digest/static/src/img/avatar.gif'

        digest_tip = self.env['digest.tip'].create({
            'name': 'test digest tip',
            'tip_description': f'''
                <div>
                    <p class="tip_title">Tip: Click on an avatar to chat with a user</p>
                    <p class="tip_content">Have a question about a document? Click on the responsible user's picture to start a conversation. If his avatar has a green dot, he is online.</p>
                    <img src="{image_local_link}" class="illustration_border" />
                </div>''',
            'user_ids': [(1)],
        })

        img_base64_data_src = False
        with open(get_module_resource('digest', 'static/src/img/avatar.gif'), 'rb') as f:
            img_base_64 = b64encode(f.read()).decode('ascii')
            img_base64_data_src = f'data:image/gif;base64,{img_base_64}'

        new_img_src = f'<img src="{img_base64_data_src}" class="illustration_border">'

        with self.mock_mail_gateway():
            digest.action_send()

        for mail in self._new_mails:
            self.assertIn(new_img_src, mail.body_html, "correct src with base64 data should be available in mail body")
            self.assertNotIn(image_local_link, mail.body_html, "local src should not be there in mail body")

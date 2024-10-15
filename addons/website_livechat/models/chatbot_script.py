# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import im_livechat


class ChatbotScript(im_livechat.ChatbotScript):

    def action_test_script(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/chatbot/%s/test' % self.id,
            'target': 'self',
        }

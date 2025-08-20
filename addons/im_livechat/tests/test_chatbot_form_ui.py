# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tests.tagged("post_install", "-at_install")
class TestLivechatChatbotFormUI(HttpCaseWithUserDemo):
    def test_chatbot_steps_sequence_ui(self):
        """ As sequences are *critical* for the chatbot_script script, let us a run a little tour that
        creates a few steps, then verify sequences are properly applied. """

        self.start_tour(
            '/odoo',
            'im_livechat_chatbot_steps_sequence_tour',
            login='admin',
        )

        chatbot_script = self.env['chatbot.script'].search([('title', '=', 'Test Chatbot Sequence')])

        self.assertEqual(len(chatbot_script.script_step_ids), 3)

        self.assertEqual(chatbot_script.script_step_ids[0].message, "<p>Step 1</p>")
        self.assertEqual(chatbot_script.script_step_ids[0].sequence, 0)
        self.assertEqual(chatbot_script.script_step_ids[1].message, "<p>Step 2</p>")
        self.assertEqual(chatbot_script.script_step_ids[1].sequence, 1)
        self.assertEqual(chatbot_script.script_step_ids[2].message, "<p>Step 3</p>")
        self.assertEqual(chatbot_script.script_step_ids[2].sequence, 2)

    def test_chatbot_steps_sequence_with_move_ui(self):
        """ Same as above, with more steps and a drag&drop within the tour.

        It is important to test those separately, as we want proper sequences even if we don't
        move records around. """

        self.start_tour(
            '/odoo',
            'im_livechat_chatbot_steps_sequence_with_move_tour',
            login='admin',
        )

        chatbot_script = self.env['chatbot.script'].search([('title', '=', 'Test Chatbot Sequence')])

        self.assertEqual(len(chatbot_script.script_step_ids), 6)

        # during the test, we create the steps normally and then move 'Step 5'
        # in second position -> check order is correct

        self.assertEqual(chatbot_script.script_step_ids[0].message, "<p>Step 1</p>")
        self.assertEqual(chatbot_script.script_step_ids[0].sequence, 0)
        self.assertEqual(chatbot_script.script_step_ids[1].message, "<p>Step 5</p>")
        self.assertEqual(chatbot_script.script_step_ids[1].sequence, 1)
        self.assertEqual(chatbot_script.script_step_ids[2].message, "<p>Step 2</p>")
        self.assertEqual(chatbot_script.script_step_ids[2].sequence, 2)
        self.assertEqual(chatbot_script.script_step_ids[3].message, "<p>Step 3</p>")
        self.assertEqual(chatbot_script.script_step_ids[3].sequence, 3)
        self.assertEqual(chatbot_script.script_step_ids[4].message, "<p>Step 4</p>")
        self.assertEqual(chatbot_script.script_step_ids[4].sequence, 4)
        self.assertEqual(chatbot_script.script_step_ids[5].message, "<p>Step 6</p>")
        self.assertEqual(chatbot_script.script_step_ids[5].sequence, 5)

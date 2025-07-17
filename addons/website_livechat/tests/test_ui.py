# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests, _
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


@tests.tagged('post_install', '-at_install')
class TestLivechatUI(HttpCaseWithUserDemo, TestLivechatCommon):
    def setUp(self):
        super().setUp()
        self.visitor_tour = self.env['website.visitor'].create({
            'access_token': 'f9d2e784d3d96a904fca2f5e2a559a19',
            'website_id': self.env.ref('website.default_website').id,
        })
        self.target_visitor = self.visitor_tour

    def test_complete_rating_flow_ui(self):
        self.start_tour("/", 'website_livechat_complete_flow_tour')
        self._check_end_of_rating_tours()

    def test_complete_rating_flow_ui_logged_in(self):
        self.start_tour("/", "website_livechat_complete_flow_tour_logged_in", login=self.user_employee.login)
        self._check_end_of_rating_tours()

    def test_happy_rating_flow_ui(self):
        self.start_tour("/", 'website_livechat_happy_rating_tour')
        self._check_end_of_rating_tours()

    def test_ok_rating_flow_ui(self):
        self.start_tour("/", 'website_livechat_ok_rating_tour')
        self._check_end_of_rating_tours()

    def test_bad_rating_flow_ui(self):
        self.start_tour("/", 'website_livechat_sad_rating_tour')
        self._check_end_of_rating_tours()

    def test_no_rating_flow_ui(self):
        self.start_tour("/", 'website_livechat_no_rating_tour')
        channel = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor_tour.id)])
        self.assertEqual(len(channel), 1, "There can only be one channel created for 'Visitor Tour'.")
        self.assertTrue(channel.livechat_end_dt, 'Livechat must be inactive after closing the chat window.')

    def test_no_rating_no_close_flow_ui(self):
        self.start_tour("/", 'website_livechat_no_rating_no_close_tour')
        channel = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor_tour.id)])
        self.assertEqual(len(channel), 1, "There can only be one channel created for 'Visitor Tour'.")
        self.assertFalse(
            channel.livechat_end_dt,
            "Livechat must be active while the chat window is not closed.",
        )

    def test_empty_chat_request_flow_no_rating_no_close_ui(self):
        # Open an empty chat request
        self.visitor_tour.with_user(self.operator).sudo().action_send_chat_request()
        chat_request = self.env["discuss.channel"].search(
            [("livechat_visitor_id", "=", self.visitor_tour.id), ("livechat_end_dt", "=", False)]
        )

        # Visitor ask a new livechat session before the operator start to send message in chat request session
        self.start_tour("/", 'website_livechat_no_rating_no_close_tour')

        # Visitor's session must be active (gets the priority)
        channel = self.env["discuss.channel"].search(
            [("livechat_visitor_id", "=", self.visitor_tour.id), ("livechat_end_dt", "=", False)]
        )
        self.assertEqual(len(channel), 1, "There can only be one channel created for 'Visitor Tour'.")
        self.assertFalse(
            channel.livechat_end_dt,
            "Livechat must be active while the chat window is not closed.",
        )

        # Check that the chat request has been canceled.
        chat_request.invalidate_recordset()
        self.assertTrue(
            chat_request.livechat_end_dt,
            "The livechat request must be inactive as the visitor started himself a livechat session.",
        )

    def test_chat_request_flow_with_rating_ui(self):
        # Open a chat request
        self.visitor_tour.with_user(self.operator).sudo().action_send_chat_request()
        chat_request = self.env["discuss.channel"].search(
            [("livechat_visitor_id", "=", self.visitor_tour.id), ("livechat_end_dt", "=", False)]
        )

        # Operator send a message to the visitor
        self._send_message(chat_request, self.operator.email, "Hello my friend !", author_id=self.operator.partner_id.id)
        self.assertEqual(len(chat_request.message_ids), 1, "Number of messages incorrect.")

        # Visitor comes to the website and receives the chat request
        self.start_tour("/", "website_livechat_chat_request")
        self._check_end_of_rating_tours()

    def _check_end_of_rating_tours(self):
        channel = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor_tour.id)])
        self.assertEqual(len(channel), 1, "There can only be one channel created for 'Visitor Tour'.")
        self.assertTrue(channel.livechat_end_dt, "Livechat must be inactive after rating.")

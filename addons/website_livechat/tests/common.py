# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, tests


class TestLivechatCommon(tests.TransactionCase):
    def setUp(self):
        super(TestLivechatCommon, self).setUp()
        self.base_datetime = fields.Datetime.from_string("2019-11-11 21:30:00")

        self.group_user = self.env.ref('base.group_user')
        self.group_livechat_user = self.env.ref('im_livechat.im_livechat_group_user')
        self.operator = self.env['res.users'].create({
            'name': 'Operator Michel',
            'login': 'operator',
            'email': 'operator@example.com',
            'password': "ideboulonate",
            'livechat_username': 'El Deboulonnator',
            'groups_id': [(6, 0, [
                self.group_user.id,
                self.group_livechat_user.id,
            ])],
        })

        self.livechat_channel = self.env['im_livechat.channel'].create({
            'name': 'The basic channel',
            'user_ids': [(6, 0, [self.operator.id])]
        })

        self.max_sessions_per_operator = 5
        visitor_vals = {
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': self.env.ref('website.default_website').id,
        }
        self.visitors = self.env['website.visitor'].create([{
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.de').id,
            'website_id': self.env.ref('website.default_website').id,
            'partner_id': self.env.ref('base.user_demo').partner_id.id,
        }] + [visitor_vals]*self.max_sessions_per_operator)
        self.visitor_demo, self.visitor = self.visitors[0], self.visitors[1]

        base_url = self.livechat_channel.get_base_url()

        self.open_chat_url = base_url + "/im_livechat/get_session"
        self.open_chat_params = {'params': {
            'channel_id': self.livechat_channel.id,
            'anonymous_name': "Wrong Name"
        }}

        self.send_feedback_url = base_url + "/im_livechat/feedback"
        self.leave_session_url = base_url + "/im_livechat/visitor_leave_session"
        self.message_info_url = base_url + "/mail/init_messaging"

        # override the get_available_users to return only Michel as available
        operators = self.operator
        def get_available_users(self):
            return operators
        self.patch(type(self.env['im_livechat.channel']), '_get_available_users', get_available_users)

        # override the _get_visitor_from_request to return self.visitor
        self.target_visitor = self.visitor
        def get_visitor_from_request(self_mock, **kwargs):
            return self.target_visitor
        self.patch(type(self.env['website.visitor']), '_get_visitor_from_request', get_visitor_from_request)

    def _send_message(self, channel, email_from, body, author_id=False):
        # As bus is unavailable in test mode, we cannot call /mail/chat_post route to post a message.
        # Instead, we post directly the message on the given channel.
        channel.with_context(mail_create_nosubscribe=True) \
            .message_post(author_id=author_id, email_from=email_from, body=body,
                          message_type='comment', subtype_id=self.env.ref('mail.mt_comment').id)

    def _send_rating(self, channel, visitor, rating_value, reason=False):
        channel_messages_count = len(channel.message_ids)

        rating_to_emoji = {1: "😞", 3: "😐", 5: "😊"}
        self.opener.post(url=self.send_feedback_url, json={'params': {
            'uuid': channel.uuid,
            'rate': rating_value,
            'reason': reason,
        }})
        res_model_id = self.env['ir.model'].sudo().search([('model', '=', channel._name)], limit=1).id
        rating = self.env['rating.rating'].search([('res_id', '=', channel.id), ('res_model_id', '=', res_model_id)])
        self.assertEqual(rating.rating, rating_value, "The rating is not correct.")

        message = "Rating: %s" % rating_to_emoji[rating_value]
        if reason:
            message += " \n%s" % reason

        self._send_message(channel, visitor.display_name, message, author_id=False)
        self.assertEqual(len(channel.message_ids), channel_messages_count + 1)

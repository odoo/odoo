# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.tests.common import tagged, HttpCase
from odoo.addons.mail.tests.common import MailCommon


@tagged('-at_install', 'post_install')
class TestDiscussChannelExpand(HttpCase, MailCommon):

    def test_channel_expand_tour(self):
        testuser = self.env['res.users'].create({
            'email': 'testuser@testuser.com',
            'groups_id': [(6, 0, [self.ref('base.group_user')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        DiscussChannelAsUser = self.env['discuss.channel'].with_user(testuser)
        channel = DiscussChannelAsUser.channel_create(name="test-mail-channel-expand-tour", group_id=self.ref("base.group_user"))
        channel.channel_member_ids.filtered(lambda m: m.is_self)._channel_fold(state='open', state_count=0)
        channel.message_post(
            body=Markup("<p>test-message-mail-channel-expand-tour</p>"),
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )
        # clear all bus notifications, so that tour does not replay old notifications
        # on a more recent state with init_messaging
        self._reset_bus()
        self.start_tour("/odoo", 'mail_enterprise/static/tests/tours/discuss_channel_expand_test_tour.js', login='testuser')

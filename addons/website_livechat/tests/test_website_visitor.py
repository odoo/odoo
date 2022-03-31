# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTests
from odoo.tests import tagged


@tagged('website_visitor')
class WebsiteVisitorTestsLivechat(WebsiteVisitorTests):

    def test_link_to_visitor_livechat(self):
        """ Same as parent's 'test_link_to_visitor' except we also test that conversations
        are merged into main visitor. """
        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])
        all_mail_channels = (main_visitor + linked_visitor).mail_channel_ids
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        # conversations of both visitors should be merged into main one
        self.assertEqual(len(main_visitor.mail_channel_ids), 2)
        self.assertEqual(main_visitor.mail_channel_ids, all_mail_channels)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        test_partner = self.env['res.partner'].create({'name': 'John Doe'})
        values.update({
            'partner_id': test_partner.id,
            'mail_channel_ids': [(0, 0, {
                'name': 'Conversation 1'
            })]
        })
        return values

    def _prepare_linked_visitor_data(self):
        values = super()._prepare_linked_visitor_data()
        values.update({
            'mail_channel_ids': [(0, 0, {
                'name': 'Conversation 2'
            })]
        })
        return values

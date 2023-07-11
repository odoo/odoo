# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common


class TestAttendee(common.SlidesCase):

    def test_course_attendee_copy(self):
        """ To check members of the channel after duplication of contact """
        # Adding attendee
        self.channel._action_add_members(self.customer)
        self.channel.invalidate_cache()

        # Attendee count before copy of contact
        attendee_before = self.env['slide.channel.partner'].search_count([])

        # Duplicating the contact
        self.customer.copy()

        # Attendee count after copy of contact
        attendee_after = self.env['slide.channel.partner'].search_count([])
        self.assertEqual(attendee_before, attendee_after, "Duplicating the contact should not create a new attendee")

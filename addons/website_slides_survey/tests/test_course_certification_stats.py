# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.survey.tests.common import TestSurveyCommon


class TestCourseCertificationStats(TestSurveyCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create certifications
        cls.certifications = cls.env["survey.survey"].create([{
            "title": f"certification {i + 1}",
            "scoring_type": "scoring_with_answers",
            "certification": True,
        } for i in range(3)])

        # Create courses and link them to certifications
        [cls.course_1, cls.course_2, cls.course_3] = cls.env["slide.channel"].create([{
            "name": f"Course {i +1}",
            "enroll": "public",
            "is_published": True,
            "slide_ids": [Command.create({
                    "name": f"Certification {i + 1} slide",
                    "slide_category": "certification",
                    "survey_id": cls.certifications.ids[i],
                    "is_published": True,
            })]} for i in range(3)])

        # Create course participants
        cls.participants = cls.survey_user + cls.user_emp + cls.user_portal
        cls.courses = cls.course_1 + cls.course_2 + cls.course_3
        cls.partner_memberships = cls.courses._action_add_members(cls.participants.partner_id)

        # Set certified/not certified participants
        cls.slide_partners = cls.env["slide.slide.partner"].create([{
            "channel_id": slide.channel_id.id,
            "partner_id": partner.id,
            "slide_id": slide.id,
        } for slide in cls.courses.slide_ids for partner in cls.participants.partner_id])

        cls.slide_partners[0].survey_scoring_success = True  # survey_user certified for course_1
        cls.slide_partners[-1].survey_scoring_success = True  # user_portal certified for course_3
        cls.slide_partners._recompute_completion()  # update slide_channel_partner.survey_certification_success

    def test_membership_certification_fields(self):
        self.assertEqual(self.course_1.members_certified_count, 1)
        self.assertEqual(self.course_2.members_certified_count, 0)
        self.assertEqual(self.course_3.members_certified_count, 1)

        certified_partners_memberships = self.partner_memberships.filtered(lambda membership: (
            membership.channel_id == self.course_1 and membership.partner_id == self.survey_user.partner_id) or (
                membership.channel_id == self.course_3 and membership.partner_id == self.user_portal.partner_id))
        non_certified_partners_memberships = self.partner_memberships - certified_partners_memberships

        self.assertTrue(all(certified_partners_memberships.mapped('survey_certification_success')))
        self.assertFalse(any(non_certified_partners_memberships.mapped('survey_certification_success')))

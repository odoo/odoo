from odoo.tests.common import TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestHrSkillsSlides(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            email="officer@example.com",
            groups="base.group_user,website_slides.group_website_slides_officer",
            login="user_officer",
            name="Ophélie Officer",
            notification_type="email",
        )
        cls.employee = cls.env["hr.employee"].create(
            [
                {
                    "name": "Test employee",
                    "user_id": cls.user.id,
                }
            ]
        )
        cls.channel = (
            cls.env["slide.channel"]
            .with_user(cls.user)
            .create(
                {
                    "name": "Test Channel",
                    "channel_type": "documentation",
                    "promote_strategy": "most_voted",
                    "enroll": "public",
                    "visibility": "public",
                    "is_published": True,
                    "karma_gen_channel_finish": 100,
                    "karma_gen_channel_rank": 10,
                }
            )
        )
        cls.slide = (
            cls.env["slide.slide"]
            .with_user(cls.user)
            .create(
                {
                    "name": "How To Cook Humans",
                    "channel_id": cls.channel.id,
                    "slide_category": "document",
                    "is_published": True,
                    "completion_time": 2.0,
                    "sequence": 1,
                }
            )
        )

    def test_add_resume_line_after_complete(self):
        self.channel.sudo()._action_add_members(self.user.partner_id)
        self.env["slide.slide.partner"].create(
            [
                {
                    "channel_id": self.channel.id,
                    "completed": True,
                    "partner_id": self.user.partner_id.id,
                    "slide_id": self.slide.id,
                }
            ]
        )
        self.assertEqual(len(self.employee.resume_line_ids), 1)
        resume_line = self.employee.resume_line_ids.filtered(lambda rl: rl.channel_id)
        self.assertEqual(resume_line.channel_id.id, self.channel.id)
        self.assertEqual(resume_line.course_url, self.channel.website_absolute_url)

    def test_remove_resume_line_no_readd(self):
        self.channel.sudo()._action_add_members(self.user.partner_id)
        channel_partner = self.env["slide.slide.partner"].create(
            [
                {
                    "channel_id": self.channel.id,
                    "completed": True,
                    "partner_id": self.user.partner_id.id,
                    "slide_id": self.slide.id,
                }
            ]
        )
        resume_line = self.employee.resume_line_ids.filtered(lambda rl: rl.channel_id)
        self.assertEqual(resume_line.channel_id.id, self.channel.id)
        resume_line.unlink()
        channel_partner._recompute_completion()
        self.assertEqual(len(self.employee.resume_line_ids), 0)

    def test_two_courses_completed_together_give_two_resume_lines(self):
        second_channel = self.env["slide.channel"].create(
            {
                "name": "Second Channel",
                "channel_type": "documentation",
                "enroll": "public",
                "visibility": "public",
                "is_published": True,
            }
        )
        second_slide = self.env["slide.slide"].create(
            {
                "name": "Second slide",
                "channel_id": second_channel.id,
                "slide_category": "document",
                "is_published": True,
            }
        )
        (self.channel | second_channel).sudo()._action_add_members(self.user.partner_id)
        self.env["slide.slide.partner"].create(
            [
                {
                    "channel_id": slide.channel_id.id,
                    "completed": True,
                    "partner_id": self.user.partner_id.id,
                    "slide_id": slide.id,
                }
                for slide in (self.slide, second_slide)
            ]
        )
        self.assertEqual(
            self.employee.resume_line_ids.channel_id, self.channel | second_channel
        )

    def test_the_completion_is_logged_on_the_learner_not_on_whoever_records_it(self):
        officer = mail_new_test_user(
            self.env,
            email="manager@example.com",
            groups="base.group_user,website_slides.group_website_slides_manager",
            login="slides_manager",
            name="Recording Manager",
        )
        officer_employee = self.env["hr.employee"].create(
            {"name": "Recording manager", "user_id": officer.id}
        )
        self.channel.sudo()._action_add_members(self.user.partner_id)
        learner_messages = len(self.employee.message_ids)
        officer_messages = len(officer_employee.message_ids)

        self.env["slide.slide.partner"].with_user(officer).create(
            {
                "channel_id": self.channel.id,
                "completed": True,
                "partner_id": self.user.partner_id.id,
                "slide_id": self.slide.id,
            }
        )

        self.assertEqual(len(officer_employee.message_ids), officer_messages)
        self.assertEqual(len(self.employee.message_ids), learner_messages + 1)

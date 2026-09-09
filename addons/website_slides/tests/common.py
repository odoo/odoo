from odoo import Command

from odoo.addons.mail.tests.common import MailCase, mail_new_test_user


class SlidesCase(MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.ref("base.user_admin").write(
            {
                "email": "mitchell.admin@example.com",
            }
        )

        cls.user_officer = mail_new_test_user(
            cls.env,
            email="officer@example.com",
            groups="base.group_user,website_slides.group_website_slides_officer",
            login="user_officer",
            name="Ophélie Officer",
            notification_type="email",
        )

        cls.user_manager = mail_new_test_user(
            cls.env,
            email="manager@example.com",
            login="user_manager",
            groups="base.group_user,website_slides.group_website_slides_manager",
            name="Manuel Manager",
            notification_type="email",
        )

        cls.user_emp = mail_new_test_user(
            cls.env,
            email="employee@example.com",
            groups="base.group_user",
            login="user_emp",
            name="Eglantine Employee",
            notification_type="email",
        )

        cls.user_portal = mail_new_test_user(
            cls.env,
            email="portal@example.com",
            groups="base.group_portal",
            login="user_portal",
            name="Patrick Portal",
            notification_type="email",
        )

        cls.user_public = mail_new_test_user(
            cls.env,
            email="public@example.com",
            groups="base.group_public",
            login="user_public",
            name="Pauline Public",
            notification_type="email",
        )

        cls.customer = cls.env["res.partner"].create(
            {
                "country_id": cls.env.ref("base.be").id,
                "email": "customer@customer.example.com",
                "phone_ids": [
                    Command.create({"number": "0456001122", "type": "landline"})
                ],
                "name": "Caroline Customer",
            }
        )

        cls.channel = (
            cls.env["slide.channel"]
            .with_user(cls.user_officer)
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
            .with_user(cls.user_officer)
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
        cls.category = (
            cls.env["slide.slide"]
            .with_user(cls.user_officer)
            .create(
                {
                    "name": "Cooking Tips for Humans",
                    "channel_id": cls.channel.id,
                    "is_category": True,
                    "is_published": True,
                    "sequence": 2,
                }
            )
        )
        cls.slide_2 = (
            cls.env["slide.slide"]
            .with_user(cls.user_officer)
            .create(
                {
                    "name": "How To Cook For Humans",
                    "channel_id": cls.channel.id,
                    "slide_category": "document",
                    "is_published": True,
                    "completion_time": 3.0,
                    "sequence": 3,
                }
            )
        )
        cls.slide_3 = (
            cls.env["slide.slide"]
            .with_user(cls.user_officer)
            .create(
                {
                    "name": "How To Cook Humans For Humans",
                    "channel_id": cls.channel.id,
                    "slide_category": "document",
                    "is_published": True,
                    "completion_time": 1.5,
                    "sequence": 4,
                    "quiz_first_attempt_reward": 42,
                }
            )
        )
        cls.slide_3._check_quiz_survey()
        cls.quiz_survey = cls.slide_3.survey_id
        cls.question_1 = (
            cls.env["survey.question"]
            .sudo()
            .create(
                {
                    "title": "How long should be cooked a human?",
                    "survey_id": cls.quiz_survey.id,
                    "question_type": "simple_choice",
                }
            )
        )
        cls.answer_1 = (
            cls.env["survey.question.answer"]
            .sudo()
            .create(
                {
                    "question_id": cls.question_1.id,
                    "value": "25' at 180°C",
                    "is_correct": True,
                    "answer_score": 1.0,
                }
            )
        )
        cls.answer_2 = (
            cls.env["survey.question.answer"]
            .sudo()
            .create(
                {
                    "question_id": cls.question_1.id,
                    "value": "Raw",
                    "is_correct": False,
                    "answer_score": 0.0,
                }
            )
        )

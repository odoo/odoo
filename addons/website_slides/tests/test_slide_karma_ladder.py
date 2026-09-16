from odoo.tests import tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_slides.tests import common


@tagged("post_install", "-at_install")
class TestQuizRewardLadder(common.SlidesCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slide_3.sudo().write(
            {
                "quiz_first_attempt_reward": 40,
                "quiz_second_attempt_reward": 30,
                "quiz_third_attempt_reward": 20,
                "quiz_fourth_attempt_reward": 10,
            }
        )
        cls.learner = mail_new_test_user(
            cls.env,
            email="ladder@example.com",
            groups="base.group_portal",
            login="user_ladder",
            name="Lars Ladder",
        )
        cls.channel._action_add_members(cls.learner.partner_id)

    def test_reward_for_a_finished_attempt(self):
        slide = self.slide_3
        self.assertEqual(slide._get_quiz_reward(1), 40)
        self.assertEqual(slide._get_quiz_reward(2), 30)
        self.assertEqual(slide._get_quiz_reward(3), 20)
        self.assertEqual(slide._get_quiz_reward(4), 10)

    def test_reward_saturates_past_the_last_step(self):
        for attempts in (5, 6, 50):
            self.assertEqual(self.slide_3._get_quiz_reward(attempts), 10)

    def test_reward_for_the_next_attempt_is_off_by_one(self):
        slide = self.slide_3
        self.assertEqual(slide._get_quiz_reward(0, done=False), 40)
        self.assertEqual(slide._get_quiz_reward(1, done=False), 30)
        self.assertEqual(slide._get_quiz_reward(3, done=False), 10)
        self.assertEqual(slide._get_quiz_reward(9, done=False), 10)

    def test_reward_is_zero_without_questions(self):
        self.assertFalse(self.slide.has_questions)
        self.assertEqual(self.slide._get_quiz_reward(1), 0)

    def test_every_reader_of_the_ladder_agrees(self):
        slide = self.slide_3.with_user(self.learner)
        slide._action_set_viewed(self.learner.partner_id, quiz_attempts_inc=True)
        slide._action_mark_completed()
        self.env.flush_all()

        info = self.slide_3._get_quiz_info(self.learner.partner_id)[self.slide_3.id]
        self.assertEqual(info["quiz_karma_won"], 40, "what attempt 1 earned")
        self.assertEqual(info["quiz_karma_gain"], 30, "what attempt 2 would earn")
        self.assertEqual(info["quiz_karma_max"], 40)

        earned = self.channel._get_earned_karma(self.learner.partner_id.ids)
        quiz_entries = [
            entry
            for entry in earned[self.learner.partner_id.id]
            if entry["karma"] == 40
        ]
        self.assertTrue(
            quiz_entries, "_get_earned_karma must read the same ladder as the payer"
        )

    def test_quiz_reset_refunds_the_karma_it_granted(self):
        slide = self.slide_3.with_user(self.learner)
        for _cycle in range(3):
            slide._action_set_viewed(self.learner.partner_id, quiz_attempts_inc=True)
            slide._action_mark_completed()
            self.env.flush_all()
            self.learner.invalidate_recordset()
            self.assertGreater(self.learner.karma, 0)

            slide.action_mark_uncompleted()
            self.env.flush_all()
            self.learner.invalidate_recordset()
            self.assertEqual(
                self.learner.karma,
                0,
                "un-completing must give back exactly what completing granted",
            )

    def test_reward_decays_across_retries(self):
        slide = self.slide_3.with_user(self.learner)
        granted = []
        for _cycle in range(3):
            slide._action_set_viewed(self.learner.partner_id, quiz_attempts_inc=True)
            slide._action_mark_completed()
            self.env.flush_all()
            self.learner.invalidate_recordset()
            granted.append(self.learner.karma)
            slide.action_mark_uncompleted()
            self.env.flush_all()
            self.learner.invalidate_recordset()
        self.assertEqual(granted, [40, 30, 20])

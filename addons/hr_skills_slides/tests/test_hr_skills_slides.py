# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import RecordCapturer, tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrSkillsSlides(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            email='officer@example.com',
            groups='base.group_user,website_slides.group_website_slides_officer',
            login='user_officer',
            name='Ophélie Officer',
            notification_type='email',
        )
        cls.employee = cls.env['hr.employee'].create([{
            'name': 'Test employee',
            'user_id': cls.user.id,
        }])
        cls.channel = cls.env['slide.channel'].with_user(cls.user).create({
            'name': 'Test Channel',
            'channel_type': 'documentation',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
            'karma_gen_channel_finish': 100,
            'karma_gen_channel_rank': 10,
        })
        cls.slide = cls.env['slide.slide'].with_user(cls.user).create({
            'name': 'How To Cook Humans',
            'channel_id': cls.channel.id,
            'slide_category': 'document',
            'is_published': True,
            'completion_time': 2.0,
            'sequence': 1,
        })

    def test_add_resume_line_after_complete(self):
        """
        Ensure that a resume line is added after that a eLearning course has been completed.
        """
        self.channel.sudo()._action_add_members(self.user.partner_id)
        self.env['slide.slide.partner'].create([{
            'channel_id': self.channel.id,
            'completed': True,
            'partner_id': self.user.partner_id.id,
            'slide_id': self.slide.id,
        }])
        self.assertEqual(len(self.employee.resume_line_ids), 1)
        resume_line = self.employee.resume_line_ids.filtered(lambda rl: rl.channel_id)
        self.assertEqual(resume_line.channel_id.id, self.channel.id)
        self.assertEqual(resume_line.course_url, self.channel.website_absolute_url)

    def test_no_duplicate_subscribe_message_on_reenroll(self):
        """
        Re-adding a partner that is already an active 'joined' member of the channel
        does not repost any message on the employee's chatter.
        """

        with RecordCapturer(self.env['mail.message'], []) as capture:
            channel = self.env['slide.channel'].create({
                'name': 'Test Channel 1',
                'enroll': 'public',
                'user_id': self.user.id,
            })
        enroll_message = capture.records.filtered(lambda m: m.model == 'hr.employee')
        self.assertEqual(enroll_message.res_id, self.employee.id)
        self.assertIn('subscribed to the course', enroll_message.body)
        self.assertIn(self.user.partner_id, channel.partner_ids)

        enroll_group = self.user.group_ids

        # add a new employee in the enrollment group
        new_user = mail_new_test_user(self.env, groups='base.group_user', login='raoul')
        new_employee = self.env['hr.employee'].create([{
            'name': 'Raoul employee',
            'user_id': new_user.id,
        }])
        enroll_group.all_user_ids |= new_user
        with RecordCapturer(self.env['mail.message'], []) as capture:
            # self.user.partner_id is already an active 'joined' member: no enroll message.
            # The new employee is not enrolled yet: an enroll message should be posted for them.
            channel.enroll_group_ids = enroll_group
        self.assertEqual(len(capture.records), 1)
        self.assertEqual(capture.records.res_id, new_employee.id)
        self.assertIn('subscribed to the course', capture.records.body)

    def test_remove_resume_line_no_readd(self):
        """
        Ensure that a eLearning resume line that is removed is not re-added when the course changes.
        """
        self.channel.sudo()._action_add_members(self.user.partner_id)
        channel_partner = self.env['slide.slide.partner'].create([{
            'channel_id': self.channel.id,
            'completed': True,
            'partner_id': self.user.partner_id.id,
            'slide_id': self.slide.id,
        }])
        resume_line = self.employee.resume_line_ids.filtered(lambda rl: rl.channel_id)
        self.assertEqual(resume_line.channel_id.id, self.channel.id)
        resume_line.unlink()
        channel_partner._recompute_completion()
        self.assertEqual(len(self.employee.resume_line_ids), 0)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import TransactionCase


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

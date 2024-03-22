# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_slides.tests import common as slides_common
from odoo.exceptions import UserError
from odoo.tests.common import users
from unittest.mock import patch


class TestSlidesManagement(slides_common.SlidesCase):

    @users('user_officer')
    def test_get_categorized_slides(self):
        new_category = self.env['slide.slide'].create({
            'name': 'Cooking Tips for Cooking Humans',
            'channel_id': self.channel.id,
            'is_category': True,
            'sequence': 5,
        })
        order = self.env['slide.slide']._order_by_strategy['sequence']
        categorized_slides = self.channel._get_categorized_slides([], order)
        self.assertEqual(categorized_slides[0]['category'], False)
        self.assertEqual(categorized_slides[1]['category'], self.category)
        self.assertEqual(categorized_slides[1]['total_slides'], 2)
        self.assertEqual(categorized_slides[2]['total_slides'], 0)
        self.assertEqual(categorized_slides[2]['category'], new_category)

    @users('user_manager')
    def test_archive(self):
        self.env['slide.slide.partner'].create({
            'slide_id': self.slide.id,
            'channel_id': self.channel.id,
            'partner_id': self.user_manager.partner_id.id,
            'completed': True
        })
        channel_partner = self.channel._action_add_members(self.user_manager.partner_id)

        self.assertTrue(self.channel.active)
        self.assertTrue(self.channel.is_published)
        self.assertFalse(channel_partner.member_status == 'completed')
        for slide in self.channel.slide_ids:
            self.assertTrue(slide.active, "All slide should be archived when a channel is archived")
            self.assertTrue(slide.is_published, "All slide should be unpublished when a channel is archived")

        self.channel.toggle_active()
        self.assertFalse(self.channel.active)
        self.assertFalse(self.channel.is_published)
        # channel_partner should still NOT be marked as completed
        self.assertFalse(channel_partner.member_status == 'completed')

        for slide in self.channel.slide_ids:
            self.assertFalse(slide.active, "All slides should be archived when a channel is archived")
            if not slide.is_category:
                self.assertFalse(slide.is_published, "All slides should be unpublished when a channel is archived, except categories")
            else:
                self.assertTrue(slide.is_published, "All slides should be unpublished when a channel is archived, except categories")

    @users('user_manager')
    def test_channel_partner_next_slide(self):
        """ Test the mechanic of the 'next_slide' field for memberships.
         Next slide should be equal to the next slide in order (sequence, id) based on completion. """

        channel = self.env['slide.channel'].create({
            'name': 'Channel1',
            'channel_type': 'documentation',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
        })

        category_1, category_2 = self.env['slide.slide'].create([{
            'name': 'Category %s' % i,
            'channel_id': channel.id,
            'is_category': True,
            'is_published': True,
        } for i in [1, 2]])

        # create 2 slides within the first category
        slide_1, slide_2 = self.env['slide.slide'].create([{
            'name': 'slide %s' % i,
            'channel_id': channel.id,
            'category_id': category_1.id,
            'slide_category': 'document',
            'is_published': True,
        } for i in [1, 2]])

        # create 2 slides within the second category
        slide_3, slide_4 = self.env['slide.slide'].create([{
            'name': 'slide %s' % i,
            'channel_id': channel.id,
            'category_id': category_2.id,
            'slide_category': 'document',
            'is_published': True,
        } for i in [3, 4]])

        self.assertEqual(channel.slide_content_ids, slide_1 | slide_2 | slide_3 | slide_4)
        # test the behavior on both employees and portal users
        users = self.user_emp | self.user_portal
        channel.sudo()._action_add_members(users.partner_id)
        memberships = self.env['slide.channel.partner'].sudo().search([('partner_id', 'in', users.partner_id.ids)])

        for membership in memberships:
            for slide in channel.slide_content_ids:
                self.assertEqual(
                    membership.next_slide_id,
                    slide,
                    'Expected %(expected_slide)s but got %(actual_slide)s' % {
                        'expected_slide': slide.name,
                        'actual_slide': membership.next_slide_id.name,
                    }
                )

                self.env['slide.slide.partner'].create({
                    'slide_id': slide.id,
                    'channel_id': channel.id,
                    'partner_id': membership.partner_id.id,
                    'completed': True
                })

                membership.invalidate_recordset(fnames=['next_slide_id'])

            # we have gone through all the content, next slide should be False
            self.assertFalse(membership.next_slide_id)

    def test_mail_completed(self):
        """ When the slide.channel is completed, an email is supposed to be sent to people that completed it. """
        channel_2 = self.env['slide.channel'].create({
            'name': 'Test Course 2',
            'slide_ids': [(0, 0, {
                'name': 'Test Slide 1'
            })]
        })
        all_users = self.user_officer | self.user_emp | self.user_portal
        all_channels = self.channel | channel_2
        all_channels.sudo()._action_add_members(all_users.partner_id)
        slide_slide_vals = []
        for slide in all_channels.slide_content_ids:
            for user in self.user_officer | self.user_emp:
                slide_slide_vals.append({
                    'slide_id': slide.id,
                    'channel_id': self.channel.id,
                    'partner_id': user.partner_id.id,
                    'completed': True
                })
        self.env['slide.slide.partner'].create(slide_slide_vals)
        created_mails = self.env['mail.mail'].search([])

        # 2 'congratulations' emails are supposed to be sent to user_officer and user_emp
        for user in self.user_officer | self.user_emp:
            self.assertTrue(
                any(mail.model == 'slide.channel.partner' and user.partner_id in mail.recipient_ids
                    for mail in created_mails)
            )
        # user_portal has not completed the course, they should not receive anything
        self.assertFalse(
            any(mail.model == 'slide.channel.partner' and self.user_portal.partner_id in mail.recipient_ids
                for mail in created_mails)
        )

    def test_mail_completed_with_different_templates(self):
        """ When the completion email is generated, it must take into account different templates. """

        mail_template = self.env['mail.template'].create({
            'model_id': self.env['ir.model']._get('slide.channel.partner').id,
            'name': 'test template',
            'partner_to': '{{ object.partner_id.id }}',
            'body_html': '<p>TestBodyTemplate2</p>',
            'subject': 'ATestSubject'
        })
        channel_2 = self.env['slide.channel'].create({
            'name': 'Test Course 2',
            'slide_ids': [(0, 0, {
                'name': 'Test Slide 2',
                'is_published': True
            })],
            'completed_template_id': mail_template.id
        })
        self.channel.completed_template_id.body_html = '<p>TestBodyTemplate</p>'

        all_channels = self.channel | channel_2
        all_channels.sudo()._action_add_members(self.user_officer.partner_id)

        with self.mock_mail_gateway():
            self.env['slide.slide.partner'].create([
                {'channel_id': self.channel.id,
                'completed': True,
                'partner_id': self.user_officer.partner_id.id,
                'slide_id': slide.id,
                }
                for slide in all_channels.slide_content_ids
            ])
        slide_created_mails = self._new_mails.filtered(lambda m: m.model == 'slide.channel.partner')
        # 2 mails should be generated from two different templates:
        # the default template and the new one
        self.assertEqual(len(slide_created_mails), 2)

        self.assertEqual(
            slide_created_mails.mapped('body'),
            ['<p>TestBodyTemplate</p>', '<p>TestBodyTemplate2</p>']
        )

        self.assertEqual(
            slide_created_mails.mapped('subject'),
            ['Congratulations! You completed %s' % self.channel.name, 'ATestSubject']
        )

    @users('user_officer')
    def test_share_without_template(self):
        channel_without_template = self.env['slide.channel'].create({
            'name': 'Course Without Template',
            'slide_ids': [(0, 0, {
                'name': 'Test Slide'
            })],
            'share_channel_template_id': False,
            'share_slide_template_id': False,
        })
        all_channels = self.channel | channel_without_template

        # try sharing the course
        with self.assertRaises(UserError) as user_error:
            all_channels._send_share_email("test@test.com")

        self.assertEqual(
            user_error.exception.args[0],
            f'Impossible to send emails. Select a "Channel Share Template" for courses {channel_without_template.name} first'
        )

        # try sharing slides
        with self.assertRaises(UserError) as user_error:
            all_channels.slide_ids._send_share_email("test@test.com", False)

        self.assertEqual(
            user_error.exception.args[0],
            f'Impossible to send emails. Select a "Share Template" for courses {channel_without_template.name} first'
        )

    def test_unlink_slide_channel(self):
        self.assertTrue(self.channel.slide_content_ids.mapped('question_ids').exists(),
            "Has question(s) linked to the slides")
        self.assertTrue(self.channel.channel_partner_ids.exists(), "Has participant(s)")

        self.channel.with_user(self.user_manager).unlink()
        self.assertFalse(self.channel.exists(),
            "Should have deleted channel along with the slides even if there are slides with quiz and participant(s)")

    def test_default_completion_time(self):
        """Verify whether the system calculates the completion time when it is not specified,
        but if the user does provide a completion time, the default time should not be applied."""

        def _get_completion_time_pdf(*args, **kwargs):
            return 13.37

        with patch(
            'odoo.addons.website_slides.models.slide_slide.Slide._get_completion_time_pdf',
            new=_get_completion_time_pdf
        ):
            slides_1 = self.env['slide.slide'].create({
                'name': 'Test_Content',
                'slide_category': 'document',
                'is_published': True,
                'is_preview': True,
                'document_binary_content': 'c3Rk',
                'channel_id': self.channel.id,
            })

            slides_2 = self.env['slide.slide'].create({
                'name': 'Test_Content',
                'slide_category': 'document',
                'is_published': True,
                'is_preview': True,
                'document_binary_content': 'c3Rk',
                'channel_id': self.channel.id,
                'completion_time': 123,
            })

        self.assertEqual(13.37, round(slides_1.completion_time, 2))
        self.assertEqual(123.0, slides_2.completion_time)

    @users('user_manager')
    def test_mail_completed_not_on_unpublishing_or_unlinking_slides(self):
        """Check that participants do not receive a course completion email when slides are deleted/unpublished."""
        def were_emails_sent():
            new_mails = self._new_mails.filtered(lambda m: m.model == 'slide.channel.partner')
            return len(new_mails) > 0

        # Setup
        self.assertGreater(len(self.channel.channel_partner_ids), self.channel.members_completed_count,
            "Channel shall have at least one participant not yet completer")
        slides_initially_published = self.channel.slide_ids.filtered('is_published')
        self.assertGreaterEqual(len(slides_initially_published), 2, "The test requires at least two published slides.")

        # Unpublishing slides
        with self.mock_mail_gateway():
            slides_initially_published[:1].is_published = False
        self.assertFalse(were_emails_sent(), "Participants should not receive emails when a slide is unpublished.")

        with self.mock_mail_gateway():
            slides_initially_published.is_published = False
        self.assertFalse(were_emails_sent(), "Participants should not receive emails when all remaining slides are unpublished.")

        # Unlinking slides
        with self.mock_mail_gateway():
            self.channel.slide_ids[:1].with_user(self.user_manager).unlink()
        self.assertFalse(were_emails_sent(), "Participants should not receive emails when a slide is deleted.")

        with self.mock_mail_gateway():
            self.channel.slide_ids.with_user(self.user_manager).unlink()
        self.assertFalse(were_emails_sent(), "Participants should not receive emails when all remaining slides are deleted.")


class TestSequencing(slides_common.SlidesCase):

    @users('user_officer')
    def test_category_update(self):
        self.assertEqual(self.channel.slide_category_ids, self.category)
        self.assertEqual(self.channel.slide_content_ids, self.slide | self.slide_2 | self.slide_3)
        self.assertEqual(self.slide.category_id, self.env['slide.slide'])
        self.assertEqual(self.slide_2.category_id, self.category)
        self.assertEqual(self.slide_3.category_id, self.category)
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.category.id, self.slide_2.id, self.slide_3.id])

        self.slide.write({'sequence': 0})
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.category.id, self.slide_2.id, self.slide_3.id])
        self.assertEqual(self.slide_2.category_id, self.category)
        self.slide_2.write({'sequence': 1})
        self.channel.invalidate_recordset()
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_2.id, self.category.id, self.slide_3.id])
        self.assertEqual(self.slide_2.category_id, self.env['slide.slide'])

        channel_2 = self.env['slide.channel'].create({
            'name': 'Test2'
        })
        new_category = self.env['slide.slide'].create({
            'name': 'NewCategorySlide',
            'channel_id': channel_2.id,
            'is_category': True,
            'sequence': 1,
        })
        new_category_2 = self.env['slide.slide'].create({
            'name': 'NewCategorySlide2',
            'channel_id': channel_2.id,
            'is_category': True,
            'sequence': 2,
        })
        new_slide = self.env['slide.slide'].create({
            'name': 'NewTestSlide',
            'channel_id': channel_2.id,
            'sequence': 2,
        })
        self.assertEqual(new_slide.category_id, new_category_2)
        (new_slide | self.slide_3).write({'sequence': 1})
        self.assertEqual(new_slide.category_id, new_category)
        self.assertEqual(self.slide_3.category_id, self.env['slide.slide'])

        (new_slide | self.slide_3).write({'sequence': 0})
        self.assertEqual(new_slide.category_id, self.env['slide.slide'])
        self.assertEqual(self.slide_3.category_id, self.env['slide.slide'])

    @users('user_officer')
    def test_resequence(self):
        self.assertEqual(self.slide.sequence, 1)
        self.category.write({'sequence': 4})
        self.slide_2.write({'sequence': 8})
        self.slide_3.write({'sequence': 3})

        self.channel.invalidate_recordset()
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, self.slide_3.id, self.category.id, self.slide_2.id])
        self.assertEqual(self.slide.sequence, 1)

        # insert a new category and check resequence_slides does as expected
        new_category = self.env['slide.slide'].create({
            'name': 'Sub-cooking Tips Category',
            'channel_id': self.channel.id,
            'is_category': True,
            'is_published': True,
            'sequence': 2,
        })
        self.env.flush_all()
        self.channel.invalidate_recordset()
        self.channel._resequence_slides(self.slide_3, force_category=new_category)
        self.assertEqual(self.slide.sequence, 1)
        self.assertEqual(new_category.sequence, 2)
        self.assertEqual(self.slide_3.sequence, 3)
        self.assertEqual(self.category.sequence, 4)
        self.assertEqual(self.slide_2.sequence, 5)
        self.assertEqual([s.id for s in self.channel.slide_ids], [self.slide.id, new_category.id, self.slide_3.id, self.category.id, self.slide_2.id])

    @users('user_officer')
    def test_channel_enroll_policy(self):
        channel = self.env['slide.channel'].create({
            'name': 'Test Course 2',
            'slide_ids': [(0, 0, {
                'name': 'Test Slide 1'
            })],
        })

        self.assertEqual(channel.visibility, 'public')
        self.assertEqual(channel.enroll, 'public')

        channel.write({'visibility': 'members'})

        self.assertEqual(channel.visibility, 'members')
        self.assertEqual(channel.enroll, 'invite')

        copied_channel = channel.copy()
        self.assertEqual(copied_channel.enroll, 'invite', "Copied channel should have the same enroll field value")

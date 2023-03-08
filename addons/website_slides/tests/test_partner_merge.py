# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import permutations

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_slides.tests import common as slides_common


class TestPartnerMerge(slides_common.SlidesCase):
    """ Check that merging partners with overlapping completion (common slides
    completed/channel enrolled) assign the union of what was done by the source
    and destination partners to the destination partner and that the karma of the
    related users stay unchanged.

    Note that as we can't merge partners linked to more than one user, each merge is
    preceded by the deletion of all users linked to the partners we merge except one.
    """

    @classmethod
    def setUpClass(cls):
        super(TestPartnerMerge, cls).setUpClass()

        cls.MergeWizard = cls.env['base.partner.merge.automatic.wizard']
        cls.channel2 = cls.env['slide.channel'].create({
            'name': 'Basics of Gardening - Test',
            'user_id': cls.env.ref('base.user_admin').id,
            'enroll': 'public',
            'channel_type': 'training',
            'allow_comment': True,
            'promote_strategy': 'most_voted',
            'is_published': True,
            'description': 'Learn the basics of gardening !',
            'karma_gen_channel_finish': 10,
            'slide_ids': [
                (0, 0, {
                    'name': 'Gardening: The Know-How',
                    'sequence': 1,
                    'slide_category': 'document',
                    'is_published': True,
                    'is_preview': True,
                })],
        })
        cls.channel.karma_gen_channel_finish = 15
        cls.channel2_slide1 = cls.channel2.slide_ids[0]
        cls.user_student0, cls.user_student1, cls.user_student2 = [
            mail_new_test_user(
                cls.env,
                email=f'student{student_n}@example.com',
                groups='base.group_portal',
                login=f'user_student{student_n}',
                name=f'Student {student_n}',
                notification_type='email',
            ) for student_n in range(3)]
        cls.user_students = cls.user_student0 + cls.user_student1 + cls.user_student2

        # Initial courses/slides membership and completion
        cls.join_course(cls.user_student0, cls.channel)
        cls.join_course(cls.user_student0, cls.channel2)
        cls.join_course(cls.user_student1, cls.channel)
        cls.join_course(cls.user_student2, cls.channel)
        cls.complete_slide(cls.user_student0, cls.slide)
        cls.complete_slide(cls.user_student0, cls.channel2_slide1)
        cls.complete_slide(cls.user_student1, cls.slide_3)
        cls.complete_slide(cls.user_student2, cls.slide_2)

        cls.merge_2_partners_permutation = list(permutations([u.partner_id.id for u in cls.user_students[:2]]))
        cls.merge_3_partners_permutation = list(permutations([u.partner_id.id for u in cls.user_students[:3]]))
        cls.user_students_initial_karma = [user.karma for user in cls.user_students]

    def merge_partners(self, partner_ids):
        self.MergeWizard._merge(partner_ids, self.env['res.partner'].browse(partner_ids[-1]))

    @classmethod
    def complete_slide(cls, user_stud, slide):
        slide_with_stud = slide.with_user(user_stud)
        if slide.question_ids:
            slide_with_stud.action_set_viewed(quiz_attempts_inc=True)
        slide_with_stud._action_mark_completed()

    @classmethod
    def join_course(cls, user_stud, channel):
        channel._action_add_members(user_stud.partner_id)

    def test_initial_values(self):
        self.assertEqual(len(self.user_students), 3)
        last_karma = -1
        for user, initial_karma in zip(self.user_students, self.user_students_initial_karma):
            self.assertEqual(user.karma, initial_karma)
            self.assertNotEqual(user.karma, last_karma)  # All karma are different
            last_karma = user.karma
        self.assertEqual(len(self.channel.partner_ids), 4)
        self.assertEqual(len(self.channel2.partner_ids), 2)

    def test_merge_0_partner(self):
        self.MergeWizard._merge(self.env['res.users'].ids)
        self.test_initial_values()  # No change must occur

    def test_merge_1_partner(self):
        self.MergeWizard._merge(self.user_student0.ids)
        self.test_initial_values()  # No change must occur

    def _test_merge_2_partners(self, partner_ids_to_merge, keep_user):
        self.user_students.filtered(lambda u: u != keep_user).unlink()  # Can't merge partners with more than one user
        karma_before_merge = keep_user.karma
        dst_partner_id = partner_ids_to_merge[-1]
        self.merge_partners(partner_ids_to_merge)

        # Check user
        self.assertEqual(keep_user.partner_id.id, dst_partner_id)
        self.assertEqual(keep_user.karma, karma_before_merge)

        # Check membership
        self.assertEqual(len(self.channel.partner_ids), 4 - 1)
        self.assertEqual(len(self.channel2.partner_ids), 2 - 0)
        self.assertIn(keep_user.partner_id, self.channel.partner_ids)
        self.assertIn(keep_user.partner_id, self.channel2.partner_ids)

        # Check completion
        self.assertTrue(self.slide.with_user(keep_user).user_has_completed)
        self.assertFalse(self.slide_2.with_user(keep_user).user_has_completed)
        self.assertTrue(self.slide_3.with_user(keep_user).user_has_completed)
        self.assertFalse(self.channel.with_user(keep_user).completed)
        self.assertTrue(self.channel2.with_user(keep_user).completed)
        self.env.invalidate_all(flush=False)

    def _test_merge_3_partners(self, partner_ids_to_merge, keep_user):
        self.user_students.filtered(lambda u: u != keep_user).unlink()
        karma_before_merge = keep_user.karma
        dst_partner_id = partner_ids_to_merge[-1]
        self.merge_partners(partner_ids_to_merge)
        self.merge_partners(partner_ids_to_merge)

        # Check user
        self.assertEqual(keep_user.partner_id.id, dst_partner_id)
        self.assertEqual(keep_user.karma, karma_before_merge)

        # Check membership
        self.assertEqual(len(self.channel.partner_ids), 4 - 2)
        self.assertEqual(len(self.channel2.partner_ids), 2 - 0)
        self.assertIn(keep_user.partner_id, self.channel.partner_ids)
        self.assertIn(keep_user.partner_id, self.channel2.partner_ids)

        # Check completion
        self.assertTrue(self.slide.with_user(keep_user).user_has_completed)
        self.assertTrue(self.slide_2.with_user(keep_user).user_has_completed)
        self.assertTrue(self.slide_3.with_user(keep_user).user_has_completed)
        self.assertTrue(self.channel.with_user(keep_user).completed)
        self.assertTrue(self.channel2.with_user(keep_user).completed)

    def test_merge_2_partners_perm0_user0(self):
        self._test_merge_2_partners(self.merge_2_partners_permutation[0], keep_user=self.user_student0)

    def test_merge_2_partners_perm1_user0(self):
        self._test_merge_2_partners(self.merge_2_partners_permutation[1], keep_user=self.user_student0)

    def test_merge_2_partners_perm1_user1(self):
        self._test_merge_2_partners(self.merge_2_partners_permutation[1], keep_user=self.user_student1)

    def test_merge_3_partners_perm0(self):
        self._test_merge_3_partners(self.merge_3_partners_permutation[0], keep_user=self.user_student0)

    def test_merge_3_partners_perm1(self):
        self._test_merge_3_partners(self.merge_3_partners_permutation[1], keep_user=self.user_student1)

    def test_merge_3_partners_perm2(self):
        self._test_merge_3_partners(self.merge_3_partners_permutation[2], keep_user=self.user_student2)

    def test_merge_3_partners_perm3(self):
        self._test_merge_3_partners(self.merge_3_partners_permutation[3], keep_user=self.user_student0)

    def test_merge_3_partners_perm4(self):
        self._test_merge_3_partners(self.merge_3_partners_permutation[4], keep_user=self.user_student1)

    def test_merge_3_partners_perm5(self):
        self._test_merge_3_partners(self.merge_3_partners_permutation[5], keep_user=self.user_student2)

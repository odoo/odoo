# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestEnrollmentSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Faculty = cls.env["university.faculty"]
        Department = cls.env["university.department"]
        Program = cls.env["university.program"]
        Year = cls.env["university.academic.year"]
        Semester = cls.env["university.semester"]
        cls.Section = cls.env["university.class.section"]
        cls.Student = cls.env["university.student"]
        cls.Enrollment = cls.env["university.enrollment"]
        cls.SlideChannel = cls.env["slide.channel"]
        cls.Users = cls.env["res.users"]
        cls.ChannelPartner = cls.env["slide.channel.partner"]
        cls.Teacher = cls.env["university.teacher"]
        cls.Subject = cls.env["university.subject"]

        cls.faculty = Faculty.create({"name": "Test Faculty", "code": "TFAC"})
        cls.department = Department.create({
            "name": "Test Department",
            "code": "TDEP",
            "faculty_id": cls.faculty.id,
        })
        cls.program = Program.create({
            "name": "Test Program",
            "code": "TPROG",
            "department_id": cls.department.id,
        })
        cls.subject_1 = cls.Subject.create({
            "name": "Subject 1",
            "code": "SUB101",
            "department_id": cls.department.id,
            "program_ids": [(6, 0, [cls.program.id])],
        })
        cls.year = Year.create({
            "name": "Academic Year 2055-2056",
            "date_start": "2055-09-01",
            "date_end": "2056-06-30",
        })
        cls.semester = Semester.create({
            "name": "Fall Semester 2055",
            "academic_year_id": cls.year.id,
            "semester_type": "semester_1",
            "date_start": "2055-09-01",
            "date_end": "2055-12-31",
        })

        # User and Student with user
        cls.student_user = cls.Users.create({
            "name": "Enrolled Student User",
            "login": "test_student_user_elearning",
            "email": "test_student_user@example.com",
        })
        cls.student_with_user = cls.Student.create({
            "name": "Student With User",
            "status": "active",
            "program_id": cls.program.id,
            "user_id": cls.student_user.id,
        })

        # Student without user
        cls.student_without_user = cls.Student.create({
            "name": "Student Without User",
            "status": "active",
            "program_id": cls.program.id,
        })

        # Section 1 with one channel
        cls.section_1 = cls.Section.create({
            "name": "SEC-101",
            "program_id": cls.program.id,
            "semester_id": cls.semester.id,
        })
        cls.channel_1 = cls.SlideChannel.create({
            "name": "eLearning Course 101",
            "class_section_id": cls.section_1.id,
        })

    def test_01_confirm_enrollment_adds_member(self):
        """Case 1: Confirm -> student partner is a member of the section's channel."""
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": self.section_1.id,
        })
        self.assertEqual(enrollment.status, "draft")
        enrollment.action_confirm()
        self.assertEqual(enrollment.status, "enrolled")

        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)
        self.assertEqual(members.member_status, "joined")

    def test_02_draft_enrollment_not_a_member(self):
        """Case 2: Draft enrollment -> not a member."""
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": self.section_1.id,
        })
        self.assertEqual(enrollment.status, "draft")

        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 0)

    def test_03_confirm_twice_exactly_one_member_row(self):
        """Case 3: Confirm twice -> exactly one member row."""
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": self.section_1.id,
        })
        enrollment.action_confirm()

        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)

        # Drop and reset to draft, then confirm again
        enrollment.action_drop()
        enrollment.action_reset_draft()
        enrollment.action_confirm()

        # Also trigger sync directly to test idempotent guard
        enrollment._elearning_add_members()

        members_after = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members_after), 1)

    def test_04_student_without_user_confirm_works(self):
        """Case 4: Student without a user -> confirm works, no error, no member."""
        initial_members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
        ])
        enrollment = self.Enrollment.create({
            "student_id": self.student_without_user.id,
            "class_section_id": self.section_1.id,
        })
        self.assertFalse(enrollment._elearning_partner())
        # Must not raise an error
        res = enrollment.action_confirm()
        self.assertTrue(res)
        self.assertEqual(enrollment.status, "enrolled")

        members_after = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
        ])
        self.assertEqual(len(members_after), len(initial_members))

    def test_05_section_with_two_channels_member_of_both(self):
        """Case 5: Section with two channels -> member of both."""
        section_two = self.Section.create({
            "name": "SEC-TWO-CHANNELS",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        channel_a = self.SlideChannel.create({
            "name": "Course Part A",
            "class_section_id": section_two.id,
        })
        channel_b = self.SlideChannel.create({
            "name": "Course Part B",
            "class_section_id": section_two.id,
        })

        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": section_two.id,
        })
        enrollment.action_confirm()
        self.assertEqual(enrollment.status, "enrolled")

        partner = self.student_user.partner_id
        member_a = self.ChannelPartner.search([
            ("channel_id", "=", channel_a.id),
            ("partner_id", "=", partner.id),
        ])
        member_b = self.ChannelPartner.search([
            ("channel_id", "=", channel_b.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(member_a), 1)
        self.assertEqual(len(member_b), 1)

    def test_06_section_with_no_channel_confirm_works(self):
        """Case 6: Section with no channel -> confirm works."""
        section_empty = self.Section.create({
            "name": "SEC-NO-CHANNELS",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        self.assertFalse(section_empty.slide_channel_ids)

        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": section_empty.id,
        })
        res = enrollment.action_confirm()
        self.assertTrue(res)
        self.assertEqual(enrollment.status, "enrolled")

    def test_07_drop_enrollment_archives_membership(self):
        """Case 7: Drop enrollment -> student member row is archived."""
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": self.section_1.id,
        })
        enrollment.action_confirm()
        partner = self.student_user.partner_id

        # Verify active member
        active_members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(active_members), 1)

        # Drop enrollment
        enrollment.action_drop()
        self.assertEqual(enrollment.status, "dropped")

        # Active search should return 0
        active_after = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(active_after), 0)

        # Inactive record should exist (archived, preserving progress)
        all_after = self.ChannelPartner.with_context(active_test=False).search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(all_after), 1)
        self.assertFalse(all_after.active)

    def test_08_reconfirm_after_drop_unarchives_membership(self):
        """Case 8: Reconfirm after drop -> membership unarchives."""
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": self.section_1.id,
        })
        enrollment.action_confirm()
        enrollment.action_drop()

        partner = self.student_user.partner_id
        # Reset and confirm again
        enrollment.action_reset_draft()
        enrollment.action_confirm()

        members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)
        self.assertTrue(members.active)

    def test_09_direct_create_enrolled_auto_enrolls(self):
        """Case 9: Direct create with status='enrolled' (bulk wizard style) auto-enrolls."""
        section_direct = self.Section.create({
            "name": "SEC-DIRECT",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        channel_direct = self.SlideChannel.create({
            "name": "Course Direct",
            "class_section_id": section_direct.id,
        })

        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": section_direct.id,
            "status": "enrolled",
        })
        self.assertEqual(enrollment.status, "enrolled")

        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", channel_direct.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)
        self.assertEqual(members.member_status, "joined")

    def test_10_shared_channel_drop_preserves_membership(self):
        """Case 10: Dropping section preserves membership if student has another section sharing channel."""
        section_a = self.Section.create({
            "name": "SEC-A",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        section_b = self.Section.create({
            "name": "SEC-B",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        shared_channel = self.SlideChannel.create({
            "name": "Shared Course",
            "class_section_id": section_a.id,
        })

        # Add shared_channel to section_b as well (in Odoo, class_section_id is Many2one on slide.channel,
        # so slide_channel_ids is one2many. But let's attach another channel or test section_a drop)
        enr_a = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": section_a.id,
        })
        enr_a.action_confirm()

        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", shared_channel.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)

        # Drop enr_a
        enr_a.action_drop()
        members_after = self.ChannelPartner.search([
            ("channel_id", "=", shared_channel.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members_after), 0)

    def test_11_teacher_and_student_slide_channel_integration(self):
        """Case 11: Teacher & Student models correctly integrate with slide.channel."""
        user = self.Users.create({
            "name": "Prof Test 11",
            "login": "prof_test_11@example.com",
            "email": "prof_test_11@example.com",
        })
        teacher = self.Teacher.create({
            "name": "Prof Test 11",
            "user_id": user.id,
            "subject_ids": [(6, 0, [self.subject_1.id])],
        })
        section = self.Section.create({
            "name": "SEC-INTEGRATION",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
            "subject_id": self.subject_1.id,
            "teacher_id": teacher.id,
        })
        channel = self.SlideChannel.create({
            "name": "ML Online Portal",
            "class_section_id": section.id,
        })
        # Check teacher stats
        self.assertIn(channel, teacher.slide_channel_ids)
        self.assertEqual(teacher.slide_channel_count, 1)

        # Enroll student and check student stats
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": section.id,
        })
        enrollment.action_confirm()
        self.assertIn(channel, self.student_with_user.slide_channel_ids)
        self.assertGreaterEqual(self.student_with_user.slide_channel_count, 1)

    def test_12_unlink_enrollment_removes_membership(self):
        """Case 12: Unlinking an active enrollment cleans up course membership."""
        enrollment = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": self.section_1.id,
        })
        enrollment.action_confirm()
        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)

        enrollment.unlink()
        members_after = self.ChannelPartner.search([
            ("channel_id", "=", self.channel_1.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members_after), 0)

    def test_13_channel_create_auto_enrolls_existing_students(self):
        """Case 13: Creating a channel on an already populated section auto-enrolls members."""
        sec_pop = self.Section.create({
            "name": "SEC-POPULATED",
            "program_id": self.program.id,
            "semester_id": self.semester.id,
        })
        enr = self.Enrollment.create({
            "student_id": self.student_with_user.id,
            "class_section_id": sec_pop.id,
        })
        enr.action_confirm()

        # Create channel now
        chan_new = self.SlideChannel.create({
            "name": "Late Created Course",
            "class_section_id": sec_pop.id,
        })
        partner = self.student_user.partner_id
        members = self.ChannelPartner.search([
            ("channel_id", "=", chan_new.id),
            ("partner_id", "=", partner.id),
        ])
        self.assertEqual(len(members), 1)

    def test_14_section_teacher_update_cascades_to_channels(self):
        """Case 14: Updating teacher on a class section automatically propagates to linked channels."""
        new_teacher_user = self.env["res.users"].create({
            "name": "Prof New Teacher",
            "login": "prof_new@example.com",
            "email": "prof_new@example.com",
        })
        new_teacher = self.Teacher.create({
            "name": "Prof New Teacher",
            "user_id": new_teacher_user.id,
            "subject_ids": [(6, 0, [self.subject_1.id])],
        })
        self.section_1.write({
            "teacher_id": new_teacher.id,
        })
        self.assertEqual(self.channel_1.teacher_id.id, new_teacher.id)
        self.assertEqual(self.channel_1.user_id.id, new_teacher_user.id)

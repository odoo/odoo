from datetime import date, timedelta
from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "school_public_holiday")
class TestHolidayNoticeBoard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PublicHoliday = cls.env["public.holiday"]
        cls.NoticeBoard = cls.env["university.notice.board"]
        cls.AcademicYear = cls.env["university.academic.year"]

        cls.admin_user = cls.env.ref("base.user_admin")

        # Find or create academic year
        cls.academic_year = cls.AcademicYear.search([], limit=1)

        # Teacher user setup
        cls.teacher_user = cls.env["res.users"].search([("login", "=", "teacher_test_notice")], limit=1)
        if not cls.teacher_user:
            cls.teacher_user = cls.env["res.users"].create({
                "name": "Teacher Notice Tester",
                "login": "teacher_test_notice",
                "email": "teacher_notice@example.com",
            })
        cls.teacher_user.write({
            "group_ids": [
                Command.link(cls.env.ref("base.group_user").id),
                Command.link(cls.env.ref("school_management.group_university_teacher").id),
                Command.link(cls.env.ref("school_management.group_school_teacher").id),
                Command.unlink(cls.env.ref("school_management.group_school_admin").id),
                Command.unlink(cls.env.ref("school_management.group_school_registrar").id),
                Command.unlink(cls.env.ref("base.group_system").id),
            ]
        })

        # Registrar user setup
        cls.registrar_user = cls.env["res.users"].search([("login", "=", "registrar_test_notice")], limit=1)
        if not cls.registrar_user:
            cls.registrar_user = cls.env["res.users"].create({
                "name": "Registrar Notice Tester",
                "login": "registrar_test_notice",
                "email": "registrar_notice@example.com",
            })
        cls.registrar_user.write({
            "group_ids": [
                Command.link(cls.env.ref("base.group_user").id),
                Command.link(cls.env.ref("school_management.group_school_registrar").id),
                Command.unlink(cls.env.ref("school_management.group_school_admin").id),
                Command.unlink(cls.env.ref("base.group_system").id),
            ]
        })

    def test_01_publish_once_creates_one_notice(self):
        """Publishing a public holiday creates exactly one notice on the Notice Board."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "National Test Holiday",
            "date_from": date(2026, 11, 10),
            "date_to": date(2026, 11, 11),
            "academic_year_id": self.academic_year.id if self.academic_year else False,
            "active": True,
        })
        # Assert no notice was auto-created upon creation
        self.assertFalse(holiday.notice_id, "Holiday should not auto-publish notice upon create.")
        notices_before = self.NoticeBoard.search([("holiday_id", "=", holiday.id)])
        self.assertEqual(len(notices_before), 0, "No notice should be linked to the holiday initially.")

        # Announce on Notice Board
        res = holiday.with_user(self.admin_user).action_publish_notice()
        self.assertTrue(holiday.notice_id, "Notice should be linked to holiday after action_publish_notice.")
        self.assertEqual(res.get("res_model"), "university.notice.board")
        self.assertEqual(res.get("res_id"), holiday.notice_id.id)

        notice = holiday.notice_id
        self.assertEqual(notice.name, holiday.name, "Notice name should match holiday name.")
        self.assertEqual(notice.notice_type, "holiday", "Notice type must be 'holiday' (Holiday & Break).")
        self.assertEqual(notice.target_audience, "all", "Audience must be 'all' (All Students & Staff).")
        self.assertEqual(notice.holiday_id, holiday, "Notice should have inverse holiday_id.")
        self.assertEqual(notice.date, holiday.date_from, "Notice date must match the holiday start date.")
        self.assertTrue(notice.active, "Notice should be active.")
        self.assertIn("National Test Holiday", notice.content, "Notice content must mention the holiday name.")
        self.assertIn("2026-11-10", notice.content, "Notice content must mention the start date.")
        self.assertIn("2026-11-11", notice.content, "Notice content must mention the end date.")

    def test_02_publishing_twice_does_not_duplicate(self):
        """Calling action_publish_notice multiple times is idempotent and never duplicates."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Idempotent Holiday",
            "date_from": date(2026, 11, 15),
            "date_to": date(2026, 11, 15),
            "active": True,
        })
        holiday.with_user(self.admin_user).action_publish_notice()
        first_notice = holiday.notice_id
        self.assertTrue(first_notice, "First notice should be created.")

        # Second publish call
        holiday.with_user(self.admin_user).action_publish_notice()
        second_notice = holiday.notice_id
        self.assertEqual(first_notice.id, second_notice.id, "Second publish must reuse existing notice.")

        all_notices = self.NoticeBoard.search([("holiday_id", "=", holiday.id)])
        self.assertEqual(len(all_notices), 1, "There must be exactly one notice for this holiday in DB.")

    def test_03_editing_holiday_updates_notice(self):
        """Updating holiday dates or name updates the linked notice in sync."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Sync Test Holiday",
            "date_from": date(2026, 11, 20),
            "date_to": date(2026, 11, 21),
            "active": True,
        })
        holiday.with_user(self.admin_user).action_publish_notice()
        notice = holiday.notice_id
        self.assertEqual(notice.name, "Sync Test Holiday")

        # Edit name and dates
        holiday.with_user(self.admin_user).write({
            "name": "Renamed Test Holiday",
            "date_from": date(2026, 11, 22),
            "date_to": date(2026, 11, 23),
        })

        self.assertEqual(notice.name, "Renamed Test Holiday", "Notice title must be synced.")
        self.assertIn("Renamed Test Holiday", notice.content, "Notice content must reflect new name.")
        self.assertIn("2026-11-22", notice.content, "Notice content must reflect new start date.")
        self.assertIn("2026-11-23", notice.content, "Notice content must reflect new end date.")

    def test_04_deactivating_holiday_archives_notice(self):
        """Deactivating/cancelling a holiday archives the linked notice."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Archiving Holiday",
            "date_from": date(2026, 12, 1),
            "date_to": date(2026, 12, 1),
            "active": True,
        })
        holiday.with_user(self.admin_user).action_publish_notice()
        notice = holiday.notice_id
        self.assertTrue(notice.active, "Notice should be active initially.")

        # Deactivate holiday
        holiday.with_user(self.admin_user).write({"active": False})
        self.assertFalse(notice.active, "Linked notice must be archived when holiday is deactivated.")

        # Reactivate holiday updates notice active status
        holiday.with_user(self.admin_user).write({"active": True})
        self.assertTrue(notice.active, "Linked notice must be reactivated when holiday is reactivated.")

    def test_05_deleting_holiday_removes_or_archives_notice(self):
        """Deleting the holiday archives or removes the linked notice, leaving no stale notice."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Deleting Holiday",
            "date_from": date(2026, 12, 5),
            "date_to": date(2026, 12, 5),
            "active": True,
        })
        holiday.with_user(self.admin_user).action_publish_notice()
        notice = holiday.notice_id

        holiday_id = holiday.id
        notice_id = notice.id

        # Delete holiday
        holiday.with_user(self.admin_user).unlink()

        notice_in_db = self.NoticeBoard.browse(notice_id)
        # Check that notice is either completely deleted or archived
        if notice_in_db.exists():
            self.assertFalse(notice_in_db.active, "Remaining notice must be archived.")
            self.assertFalse(notice_in_db.holiday_id, "holiday_id must be cleared on notice.")

        # Confirm no active notice remains for this holiday
        active_notices = self.NoticeBoard.search([("holiday_id", "=", holiday_id), ("active", "=", True)])
        self.assertEqual(len(active_notices), 0, "No active notice should remain after holiday deletion.")

    def test_06_teacher_cannot_publish(self):
        """A teacher attempting to announce a holiday on the notice board gets AccessError."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Teacher Restricted Holiday",
            "date_from": date(2026, 12, 10),
            "date_to": date(2026, 12, 10),
            "active": True,
        })
        with self.assertRaises(AccessError):
            holiday.with_user(self.teacher_user).action_publish_notice()

    def test_07_registrar_can_publish(self):
        """A registrar can publish holiday notices to the notice board."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Registrar Allowed Holiday",
            "date_from": date(2026, 12, 12),
            "date_to": date(2026, 12, 12),
            "active": True,
        })
        res = holiday.with_user(self.registrar_user).action_publish_notice()
        self.assertTrue(holiday.notice_id, "Registrar must be able to publish notice.")
        self.assertEqual(holiday.notice_id.name, "Registrar Allowed Holiday")

    def test_08_bulk_publish_server_action(self):
        """Bulk publishing multiple holidays in one go creates one notice per holiday."""
        h1 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Bulk Holiday 1",
            "date_from": date(2026, 12, 20),
            "date_to": date(2026, 12, 20),
            "active": True,
        })
        h2 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Bulk Holiday 2",
            "date_from": date(2026, 12, 21),
            "date_to": date(2026, 12, 21),
            "active": True,
        })
        holidays = h1 | h2
        res = holidays.with_user(self.admin_user).action_publish_notice()
        self.assertTrue(res, "Bulk publish should return True.")
        self.assertTrue(h1.notice_id, "Holiday 1 must have linked notice.")
        self.assertTrue(h2.notice_id, "Holiday 2 must have linked notice.")
        self.assertNotEqual(h1.notice_id.id, h2.notice_id.id, "Each holiday must have its own notice.")

    def test_09_teacher_cannot_edit_generated_notice(self):
        """Teachers cannot edit a notice created from a holiday."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Protected Admin Holiday",
            "date_from": date(2026, 12, 25),
            "date_to": date(2026, 12, 25),
            "active": True,
        })
        holiday.with_user(self.admin_user).action_publish_notice()
        notice = holiday.notice_id

        # Teacher should be able to read
        read_notice = notice.with_user(self.teacher_user)
        self.assertEqual(read_notice.name, "Protected Admin Holiday")

        # Teacher should NOT be able to modify
        with self.assertRaises(AccessError):
            read_notice.write({"name": "Hacked Holiday Title"})

    def test_10_smart_button_action_open_notice(self):
        """Smart button action_open_notice returns the correct act_window."""
        holiday = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Smart Button Holiday",
            "date_from": date(2026, 12, 30),
            "date_to": date(2026, 12, 30),
            "active": True,
        })
        # When notice is not yet set
        self.assertFalse(holiday.action_open_notice())

        # Publish notice
        holiday.with_user(self.admin_user).action_publish_notice()
        action = holiday.action_open_notice()
        self.assertEqual(action.get("type"), "ir.actions.act_window")
        self.assertEqual(action.get("res_model"), "university.notice.board")
        self.assertEqual(action.get("res_id"), holiday.notice_id.id)

    def test_11_multiday_holiday_consolidates_into_single_notice(self):
        """Multi-day holidays with Day 1, 2, 3 create only 1 combined notice row on Campus Notice Board."""
        h1 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Test Multiday Festival (Day 1)",
            "date_from": date(2027, 11, 23),
            "date_to": date(2027, 11, 23),
            "active": True,
        })
        h2 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Test Multiday Festival (Day 2)",
            "date_from": date(2027, 11, 24),
            "date_to": date(2027, 11, 24),
            "active": True,
        })
        h3 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Test Multiday Festival (Day 3)",
            "date_from": date(2027, 11, 25),
            "date_to": date(2027, 11, 25),
            "active": True,
        })
        holidays = h1 | h2 | h3
        holidays.with_user(self.admin_user).action_publish_notice()

        # Check notices on Notice Board: must be exactly ONE notice created
        notices = self.NoticeBoard.search([("holiday_id", "in", holidays.ids)])
        self.assertEqual(len(notices), 1, "Must create only 1 notice row for multi-day holiday group.")
        notice = notices[0]

        # Name should be stripped of day suffix
        self.assertEqual(notice.name, "Test Multiday Festival")
        self.assertEqual(notice.date, date(2027, 11, 23))
        self.assertIn("2027-11-23 to 2027-11-25", notice.content)
        self.assertIn("Test Multiday Festival", notice.content)

        # All three holidays must share the single notice
        self.assertEqual(h1.notice_id, notice)
        self.assertEqual(h2.notice_id, notice)
        self.assertEqual(h3.notice_id, notice)

        # Deactivating Day 3 narrows the date range on the notice
        h3.with_user(self.admin_user).write({"active": False})
        self.assertTrue(notice.active, "Notice should stay active since Day 1 and 2 are active.")
        self.assertIn("2027-11-23 to 2027-11-24", notice.content)

        # Deleting Day 2 keeps notice for Day 1
        h2.with_user(self.admin_user).unlink()
        self.assertTrue(notice.exists())
        self.assertTrue(notice.active)

        # Deactivating Day 1 archives notice
        h1.with_user(self.admin_user).write({"active": False})
        self.assertFalse(notice.active, "Notice must be archived once all days are inactive.")

    def test_12_single_publish_sequential_merges_notice(self):
        """Publishing Day 1 then Day 2 sequentially merges into the existing notice without duplicating rows."""
        h1 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Sequential Holiday Day 1",
            "date_from": date(2027, 4, 14),
            "date_to": date(2027, 4, 14),
            "active": True,
        })
        h1.with_user(self.admin_user).action_publish_notice()
        notice1 = h1.notice_id
        self.assertTrue(notice1)

        h2 = self.PublicHoliday.with_user(self.admin_user).create({
            "name": "Sequential Holiday Day 2",
            "date_from": date(2027, 4, 15),
            "date_to": date(2027, 4, 15),
            "active": True,
        })
        h2.with_user(self.admin_user).action_publish_notice()

        # Both should share the exact same notice, no new notice created
        self.assertEqual(h2.notice_id.id, notice1.id, "Day 2 must merge into existing notice.")
        all_notices = self.NoticeBoard.search([("holiday_id", "in", (h1 | h2).ids)])
        self.assertEqual(len(all_notices), 1, "There must only be 1 notice row on the Notice Board.")
        self.assertIn("2027-04-14 to 2027-04-15", notice1.content)

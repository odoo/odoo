from datetime import UTC, date, datetime, timedelta
from unittest.mock import DEFAULT, patch

from dateutil.relativedelta import relativedelta
from psycopg import IntegrityError

from odoo import exceptions, fields, tests
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.tests import Form, HttpCase, users
from odoo.tests.common import freeze_time
from odoo.tools import mute_logger

from odoo.addons.mail.models import mail_activity as mail_activity_module
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.addons.mail.tools import activity_calendar
from odoo.addons.test_mail.models.test_mail_models import MailTestActivity


class TestActivityCommon(ActivityScheduleCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record, cls.test_record_2 = cls.env["mail.test.activity"].create(
            [
                {"name": "Test"},
                {"name": "Test_2"},
            ]
        )


@tests.tagged("mail_activity")
class TestActivityRights(TestActivityCommon):
    def test_activity_action_view_document_no_access(self):
        def _employee_no_access(records, operation):
            """Simulates employee having no access to the document"""
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError(
                    "Access denied to document"
                )
            return DEFAULT

        test_activity = (
            self.env["mail.activity"]
            .with_user(self.user_admin)
            .create(
                {
                    "activity_type_id": self.env.ref("test_mail.mail_act_test_todo").id,
                    "res_model_id": self.env.ref(
                        "test_mail.model_mail_test_activity"
                    ).id,
                    "res_id": self.test_record.id,
                    "user_id": self.user_employee.id,
                    "summary": "Test Activity",
                }
            )
        )

        action = test_activity.with_user(self.user_employee).action_view_document()
        self.assertEqual(action["res_model"], self.test_record._name)
        self.assertEqual(action["res_id"], self.test_record.id)

        # If user has no access to the record, should return activity view instead
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_no_access,
        ):
            self.assertFalse(
                self.test_record.with_user(self.user_employee).has_access("read")
            )

            action = test_activity.with_user(self.user_employee).action_view_document()
            self.assertEqual(action["res_model"], "mail.activity")
            self.assertEqual(action["res_id"], test_activity.id)

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_activity_security_user_access(self):
        """Internal user can modify assigned or created or if write on document"""

        def _employee_crash(records, operation):
            """If employee is test employee, consider they have no access on document"""
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError(
                    "Hop hop hop Ernest, please step back."
                )
            return DEFAULT

        act_emp_for_adm = self.test_record.with_user(
            self.user_employee
        ).activity_schedule(
            "test_mail.mail_act_test_todo",
            user_id=self.user_admin.id,
        )
        act_emp_for_emp = self.test_record.with_user(
            self.user_employee
        ).activity_schedule(
            "test_mail.mail_act_test_todo",
            user_id=self.user_employee.id,
        )
        act_adm_for_adm = self.test_record.with_user(self.user_admin).activity_schedule(
            "test_mail.mail_act_test_todo",
            user_id=self.user_admin.id,
        )
        act_adm_for_emp = self.test_record.with_user(self.user_admin).activity_schedule(
            "test_mail.mail_act_test_todo",
            user_id=self.user_employee.id,
        )

        for activity, can_write in [
            (act_emp_for_adm, True),
            (act_emp_for_emp, True),
            (act_adm_for_adm, False),
            (act_adm_for_emp, True),
        ]:
            with self.subTest(
                user=activity.user_id.name, creator=activity.create_uid.name
            ):
                # no document access -> based on create_uid / user_id
                with patch.object(
                    MailTestActivity,
                    "_check_access",
                    autospec=True,
                    side_effect=_employee_crash,
                ):
                    activity = activity.with_user(self.user_employee)
                    self.assertEqual(activity.can_write, can_write)
                    if can_write:
                        activity.write({"summary": "Caramba"})
                    else:
                        with self.assertRaises(exceptions.AccessError):
                            activity.write({"summary": "Caramba"})

                # document access -> ok bypass
                activity.write({"summary": "Caramba caramba"})

    def test_activity_security_user_access_customized(self):
        """Test '_mail_get_operation_for_mail_message_operation' support when scheduling activities."""
        access_open, access_ro, access_locked = (
            self.env["mail.test.access.custo"]
            .with_user(self.user_admin)
            .create(
                [
                    {"name": "Open"},
                    {"name": "Open RO", "is_readonly": True},
                    {"name": "Locked", "is_locked": True},
                ]
            )
        )
        admin_activities = self.env["mail.activity"]
        for record in access_open + access_ro + access_locked:
            admin_activities += record.with_user(self.user_admin).activity_schedule(
                "test_mail.mail_act_test_todo_generic",
            )

        # sanity checks on rule implementation
        (access_open + access_ro + access_locked).with_user(
            self.user_employee
        ).check_access("read")
        access_open.with_user(self.user_employee).check_access("write")
        with self.assertRaises(exceptions.AccessError):
            (access_ro + access_locked).with_user(self.user_employee).check_access(
                "write"
            )

        # '_mail_get_operation_for_mail_message_operation' allows to post, hence posting activities
        emp_new_1 = access_open.with_user(self.user_employee).activity_schedule(
            "test_mail.mail_act_test_todo_generic",
        )
        emp_new_2 = access_ro.with_user(self.user_employee).activity_schedule(
            "test_mail.mail_act_test_todo_generic",
        )

        with self.assertRaises(exceptions.AccessError):
            access_locked.with_user(self.user_employee).activity_schedule(
                "test_mail.mail_act_test_todo_generic",
            )

        self.env.invalidate_all()
        # check read access correctly uses '_mail_get_operation_for_mail_message_operation'
        admin_activities[0].with_user(self.user_employee).read(["summary"])
        admin_activities[1].with_user(self.user_employee).read(["summary"])

        self.env.invalidate_all()
        # check search correctly uses '_get_mail_message_access'
        found = (
            self.env["mail.activity"]
            .with_user(self.user_employee)
            .search([("res_model", "=", "mail.test.access.custo")])
        )
        self.assertEqual(
            found,
            admin_activities[:2] + emp_new_1 + emp_new_2,
            "Should respect _get_mail_message_access, reading non locked records",
        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_activity_security_user_noaccess_automated(self):
        def _employee_crash(records, operation):
            """If employee is test employee, consider they have no access on document"""
            if records.env.uid == self.user_employee.id and not records.env.su:
                return records, lambda: exceptions.AccessError(
                    "Hop hop hop Ernest, please step back."
                )
            return DEFAULT

        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            _activity = self.test_record.activity_schedule(
                "test_mail.mail_act_test_todo", user_id=self.user_employee.id
            )

            activity2 = self.test_record.activity_schedule(
                "test_mail.mail_act_test_todo", user_id=self.user_admin.id
            )
            activity2.write({"user_id": self.user_employee.id})

    def test_activity_security_user_noaccess_manual(self):
        def _employee_crash(records, operation):
            """If employee is test employee, consider they have no access on document"""
            if records.env.uid == self.user_employee.id and not records.env.su:
                raise exceptions.AccessError("Hop hop hop Ernest, please step back.")
            return DEFAULT

        test_activity = (
            self.env["mail.activity"]
            .with_user(self.user_admin)
            .create(
                {
                    "activity_type_id": self.env.ref("test_mail.mail_act_test_todo").id,
                    "res_model_id": self.env.ref(
                        "test_mail.model_mail_test_activity"
                    ).id,
                    "res_id": self.test_record.id,
                    "user_id": self.user_admin.id,
                    "summary": "Summary",
                }
            )
        )
        test_activity.flush_recordset()

        # can _search activities if access to the document
        self.env["mail.activity"].with_user(self.user_employee)._search(
            [("id", "=", test_activity.id)]
        )

        # cannot _search activities if no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            with self.assertRaises(exceptions.AccessError):
                searched_activity = (
                    self.env["mail.activity"]
                    .with_user(self.user_employee)
                    ._search([("id", "=", test_activity.id)])
                )

        # can formatted_read_group activities if access to the document
        read_group_result = (
            self.env["mail.activity"]
            .with_user(self.user_employee)
            .formatted_read_group(
                [("id", "=", test_activity.id)],
                ["summary"],
                ["__count"],
            )
        )
        self.assertEqual(1, read_group_result[0]["__count"])
        self.assertEqual("Summary", read_group_result[0]["summary"])

        # cannot read_group activities if no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            with self.assertRaises(exceptions.AccessError):
                self.env["mail.activity"].with_user(
                    self.user_employee
                ).formatted_read_group(
                    [("id", "=", test_activity.id)],
                    ["summary"],
                    ["__count"],
                )

        # cannot read activities if no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            with self.assertRaises(exceptions.AccessError):
                searched_activity = (
                    self.env["mail.activity"]
                    .with_user(self.user_employee)
                    .search([("id", "=", test_activity.id)])
                )
                searched_activity.read(["summary"])

        # cannot search_read activities if no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            with self.assertRaises(exceptions.AccessError):
                self.env["mail.activity"].with_user(self.user_employee).search_read(
                    [("id", "=", test_activity.id)], ["summary"]
                )

        # can create activities for people that cannot access record
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            self.env["mail.activity"].create(
                {
                    "activity_type_id": self.env.ref("test_mail.mail_act_test_todo").id,
                    "res_model_id": self.env.ref(
                        "test_mail.model_mail_test_activity"
                    ).id,
                    "res_id": self.test_record.id,
                    "user_id": self.user_employee.id,
                }
            )

        # cannot create activities if no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            with self.assertRaises(exceptions.AccessError):
                self.test_record.with_user(self.user_employee).activity_schedule(
                    "test_mail.mail_act_test_todo", user_id=self.user_admin.id
                )

        test_activity.user_id = self.user_employee
        test_activity.flush_recordset()

        # user can read activities assigned to him even if he has no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            found = (
                self.env["mail.activity"]
                .with_user(self.user_employee)
                .search([("id", "=", test_activity.id)])
            )
            self.assertEqual(found, test_activity)
            found.read(["summary"])

        # user can read_group activities assigned to him even if he has no access to the document
        with patch.object(
            MailTestActivity,
            "_check_access",
            autospec=True,
            side_effect=_employee_crash,
        ):
            read_group_result = (
                self.env["mail.activity"]
                .with_user(self.user_employee)
                .formatted_read_group(
                    [("id", "=", test_activity.id)],
                    ["summary"],
                    ["__count"],
                )
            )
            self.assertEqual(1, read_group_result[0]["__count"])
            self.assertEqual("Summary", read_group_result[0]["summary"])


@tests.tagged("mail_activity")
class TestActivityFlow(TestActivityCommon):
    def test_activity_flow_employee(self):
        with self.with_user("employee"):
            test_record = self.env["mail.test.activity"].browse(self.test_record.id)
            self.assertEqual(test_record.activity_ids, self.env["mail.activity"])

            # employee record an activity and check the deadline
            activity = self.env["mail.activity"].create(
                {
                    "summary": "Test Activity",
                    "date_deadline": date.today() + relativedelta(days=1),
                    "activity_type_id": self.env.ref(
                        "mail.mail_activity_data_email"
                    ).id,
                    "res_model_id": self.env["ir.model"]._get(test_record._name).id,
                    "res_id": test_record.id,
                }
            )
            self.assertEqual(test_record.activity_summary, "Test Activity")
            self.assertEqual(test_record.activity_state, "planned")

            test_record.activity_ids.write(
                {"date_deadline": date.today() - relativedelta(days=1)}
            )
            self.assertEqual(test_record.activity_state, "overdue")

            test_record.activity_ids.write({"date_deadline": date.today()})
            self.assertEqual(test_record.activity_state, "today")

            # activity is done
            activity.action_feedback(feedback="So much feedback")
            self.assertEqual(activity.feedback, "So much feedback")
            self.assertEqual(test_record.activity_ids, self.env["mail.activity"])
            self.assertEqual(
                test_record.message_ids[0].subtype_id,
                self.env.ref("mail.mt_activities"),
            )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_activity_notify_other_user(self):
        self.user_admin.notification_type = "email"
        rec = self.test_record.with_user(self.user_employee)
        with self.assertSinglePostNotifications(
            [{"partner": self.partner_admin, "type": "email"}],
            message_info={
                "content": "assigned you the following activity",
                "subtype": "mail.mt_note",
                "message_type": "user_notification",
            },
        ):
            activity = rec.activity_schedule(
                "test_mail.mail_act_test_todo", user_id=self.user_admin.id
            )
        self.assertEqual(activity.create_uid, self.user_employee)
        self.assertEqual(activity.user_id, self.user_admin)

    def test_activity_notify_same_user(self):
        self.user_employee.notification_type = "email"
        rec = self.test_record.with_user(self.user_employee)
        with self.assertNoNotifications():
            activity = rec.activity_schedule(
                "test_mail.mail_act_test_todo", user_id=self.user_employee.id
            )
        self.assertEqual(activity.create_uid, self.user_employee)
        self.assertEqual(activity.user_id, self.user_employee)

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_activity_dont_notify_no_user_change(self):
        self.user_employee.notification_type = "email"
        activity = self.test_record.activity_schedule(
            "test_mail.mail_act_test_todo", user_id=self.user_employee.id
        )
        with self.assertNoNotifications():
            activity.with_user(self.user_admin).write(
                {"user_id": self.user_employee.id}
            )
        self.assertEqual(activity.user_id, self.user_employee)

    def test_activity_summary_sync(self):
        """Test summary from type is copied on activities if set (currently only in form-based onchange)"""
        ActivityType = self.env["mail.activity.type"]
        call_activity_type = ActivityType.create({"name": "call", "sequence": 1})
        email_activity_type = ActivityType.create(
            {"name": "email", "summary": "Email Summary", "sequence": "30"}
        )
        call_activity_type = ActivityType.create({"name": "call", "summary": False})
        with Form(
            self.env["mail.activity"].with_context(
                default_res_model_id=self.env["ir.model"]._get_id("mail.test.activity"),
                default_res_id=self.test_record.id,
            )
        ) as ActivityForm:
            # coming from default activity type, which is to do
            self.assertEqual(
                ActivityForm.activity_type_id,
                self.env.ref("mail.mail_activity_data_todo"),
            )
            self.assertEqual(ActivityForm.summary, "TodoSummary")
            # `res_model_id` and `res_id` are invisible, see view `mail.mail_activity_view_form_popup`
            # they must be set using defaults, see `action_feedback_schedule_next`
            ActivityForm.activity_type_id = call_activity_type
            # activity summary should be empty
            self.assertEqual(
                ActivityForm.summary, "TodoSummary", "Did not erase if void on type"
            )

            ActivityForm.activity_type_id = email_activity_type
            # activity summary should be replaced with email's default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

            ActivityForm.activity_type_id = call_activity_type
            # activity summary remains unchanged from change of activity type as call activity doesn't have default summary
            self.assertEqual(ActivityForm.summary, email_activity_type.summary)

    def test_activity_type_unlink(self):
        """Removing type should allocate activities to Todo"""
        email_activity_type = self.env["mail.activity.type"].create(
            {
                "name": "email",
                "summary": "Email Summary",
            }
        )
        temp_record = self.env["mail.test.activity"].create({"name": "Test"})
        activity = temp_record.activity_schedule(
            activity_type_id=email_activity_type.id,
            user_id=self.user_employee.id,
        )
        self.assertEqual(activity.activity_type_id, email_activity_type)
        email_activity_type.unlink()
        self.assertEqual(
            activity.activity_type_id, self.env.ref("mail.mail_activity_data_todo")
        )

        # Todo is protected, niark niark
        with self.assertRaises(exceptions.UserError):
            self.env.ref("mail.mail_activity_data_todo").unlink()

    @mute_logger("odoo.db")
    def test_activity_values(self):
        """Test activities are created with right model / res_id values linking
        to records without void values. 0 as res_id especially is not wanted."""
        # creating activities on a temporary record generates activities with res_id
        # being 0, which is annoying -> never create activities in transient mode
        temp_record = self.env["mail.test.activity"].new({"name": "Test"})
        with self.assertRaises(IntegrityError):
            activity = temp_record.activity_schedule(
                "test_mail.mail_act_test_todo", user_id=self.user_employee.id
            )

        test_record = self.env["mail.test.activity"].browse(self.test_record.ids)

        # document should be complete: both model and res_id
        with self.assertRaises(IntegrityError):
            self.env["mail.activity"].create(
                {
                    "res_model_id": self.env["ir.model"]._get_id(test_record._name),
                }
            )
        with self.assertRaises(IntegrityError):
            self.env["mail.activity"].create(
                {
                    "res_model_id": self.env["ir.model"]._get_id(test_record._name),
                    "res_id": False,
                }
            )
        with self.assertRaises(IntegrityError):
            self.env["mail.activity"].create(
                {
                    "res_id": test_record.id,
                }
            )
        # free activity is ok (no model, no res_id)
        self.env["mail.activity"].create({"user_id": self.env.uid})

        activity = self.env["mail.activity"].create(
            {
                "res_id": test_record.id,
                "res_model_id": self.env["ir.model"]._get_id(test_record._name),
            }
        )
        with self.assertRaises(IntegrityError):
            activity.write({"res_model_id": False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({"res_id": False})
            self.env.flush_all()
        with self.assertRaises(IntegrityError):
            activity.write({"res_id": 0})
            self.env.flush_all()


@tests.tagged("mail_activity", "post_install", "-at_install")
class TestActivityDoneBatch(TestActivityCommon):
    def test_marking_activities_done_posts_once_per_round_of_records(self):
        """Feedback on N activities posts their done messages in one batch per
        round of distinct records: three records with one activity each are one
        message create, a record carrying two activities needs a second round."""
        records = self.env["mail.test.activity"].create(
            [{"name": f"Done {idx}"} for idx in range(3)]
        )
        activities = self.env["mail.activity"]
        for record in records:
            activities += record.activity_schedule("mail.mail_activity_data_todo")
        activities += records[0].activity_schedule("mail.mail_activity_data_email")
        self.env.flush_all()

        Message = type(self.env["mail.message"])
        create_origin = Message.create
        create_sizes = []

        def _create(model, vals_list):
            create_sizes.append(len(vals_list))
            return create_origin(model, vals_list)

        with patch.object(Message, "create", autospec=True, side_effect=_create):
            messages, _done = activities._action_done(feedback="all done")

        self.assertEqual(len(messages), 4, "one done message per activity")
        self.assertEqual(
            sorted(create_sizes),
            [1, 3],
            "one batch for the three records, one more for the second activity of the first",
        )
        self.assertFalse(activities.filtered("active"), "done activities are archived")
        for record in records:
            done = record.message_ids.filtered(
                lambda m: m.subtype_id == self.env.ref("mail.mt_activities")
            )
            self.assertEqual(len(done), 2 if record == records[0] else 1)
            for message in done:
                self.assertIn("all done", message.body)
                self.assertEqual(message.author_id, self.env.user.partner_id)
                self.assertTrue(message.mail_activity_type_id)


class TestActivitySystray(TestActivityCommon, HttpCase):
    """Test for systray_get_activities"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_lead_records = cls.env["mail.test.multi.company.with.activity"].create(
            [
                {"name": "Test Lead 1"},
                {"name": "Test Lead 2"},
                {"name": "Test Lead 3 (to remove)"},
                {"name": "Test Lead 4 (Company2)", "company_id": cls.company_2.id},
            ]
        )
        cls.deleted_record = cls.test_lead_records[2]
        cls.dt_reference = datetime(2024, 1, 15, 8, 0, 0)

        # remove potential demo data on admin, to make test deterministic
        cls.env["mail.activity"].search([("user_id", "=", cls.user_admin.id)]).unlink()

        # records and leads and free activities
        # have 1 record (or activity) for today, one for tomorrow
        cls.test_activities = cls.env["mail.activity"]
        for record, summary, dt, creator in (
            (cls.test_record, "Summary Today'", cls.dt_reference, cls.user_employee),
            (
                cls.test_record_2,
                "Summary Tomorrow'",
                cls.dt_reference + timedelta(days=1),
                cls.user_employee,
            ),
            (
                cls.test_lead_records[0],
                "Summary Today'",
                cls.dt_reference,
                cls.user_employee,
            ),
            (
                cls.test_lead_records[1],
                "Summary Tomorrow'",
                cls.dt_reference + timedelta(days=1),
                cls.user_employee,
            ),
            (
                cls.test_lead_records[2],
                "Summary Tomorrow'",
                cls.dt_reference + timedelta(days=1),
                cls.user_employee,
            ),
            (
                cls.test_lead_records[3],
                "Summary Tomorrow'",
                cls.dt_reference + timedelta(days=1),
                cls.user_admin,
            ),
        ):
            cls.test_activities += record.with_user(creator).activity_schedule(
                "test_mail.mail_act_test_todo_generic",
                date_deadline=dt.date(),
                summary=summary,
                user_id=cls.user_employee.id,
            )

        cls.test_lead_activities = cls.test_activities[2:]
        cls.test_activities_removed = cls.deleted_record.activity_ids
        cls.test_activities_company_2 = cls.test_lead_records[3].activity_ids

        # add atttachments on lead-like test records
        cls.lead_act_attachments = cls.env["ir.attachment"].create(
            cls._generate_attachments_data(
                1, "mail.activity", cls.test_lead_activities[-4]
            )
            + cls._generate_attachments_data(
                1, "mail.activity", cls.test_lead_activities[-3]
            )
            + cls._generate_attachments_data(
                1, "mail.activity", cls.test_lead_activities[-2]
            )
            + cls._generate_attachments_data(
                1, "mail.activity", cls.test_lead_activities[-1]
            )
        )

        # free (no model) activities
        cls.test_activities_free = (
            cls.env["mail.activity"]
            .with_user(cls.user_employee)
            .create(
                [
                    {
                        "date_deadline": dt,
                        "summary": "Summary",
                        "user_id": cls.user_employee.id,
                    }
                    for dt in (cls.dt_reference, cls.dt_reference + timedelta(days=1))
                ]
            )
        )

        # In the mean time, some FK deletes the record where the message is
        # scheduled, skipping its unlink() override
        cls.env.cr.execute(
            f"DELETE FROM {cls.test_lead_records._table} WHERE id = %s",
            (cls.deleted_record.id,),
        )

        cls.env.invalidate_all()

    @users("employee")
    def test_systray_activities_for_various_records(self):
        """Check that activities made on archived or not archived records, as
        well as on removed record, to check systray activities behavior and
        robustness."""
        # archive record 1
        self.test_record.action_archive()
        self.assertTrue(
            self.test_activities[0].exists(), "Archiving record keeps activities"
        )

        self.authenticate(self.user_employee.login, self.user_employee.login)
        with freeze_time(self.dt_reference):
            groups_data = (
                self.call_jsonrpc(
                    "/mail/data", {"fetch_params": ["systray_get_activities"]}
                )
                .get("Store", {})
                .get("activityGroups", [])
            )
        self.assertEqual(
            len(groups_data),
            3,
            "Should have activities for 2 test models + generic for non accessible",
        )

        for model_name, msg, (
            exp_total,
            exp_today,
            exp_planned,
            exp_overdue,
        ), exp_domain in [
            ("mail.activity", "2 free + 2 linked to 1", (1, 1, 3, 0), []),
            (
                self.test_record._name,
                "Archived keeps activities",
                (1, 1, 1, 0),
                [["active", "in", [True, False]]],
            ),
            (
                self.test_lead_records._name,
                "Planned do not count in total",
                (1, 1, 1, 0),
                [],
            ),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(
                    values for values in groups_data if values["model"] == model_name
                )
                self.assertEqual(group_values["due_count"], exp_total)
                self.assertEqual(group_values["today_count"], exp_today)
                self.assertEqual(group_values["planned_count"], exp_planned)
                self.assertEqual(group_values["overdue_count"], exp_overdue)
                self.assertEqual(group_values["domain"], exp_domain)

        # check search results with removed records
        self.env.invalidate_all()
        test_with_removed = (
            self.env["mail.activity"]
            .sudo()
            .search(
                [
                    ("id", "in", self.test_activities.ids),
                    ("res_model", "=", self.test_lead_records._name),
                ]
            )
        )
        self.assertEqual(
            len(test_with_removed),
            4,
            "Without ACL check, activities linked to removed records are kept",
        )

        self.env.invalidate_all()
        test_with_removed_as_admin = (
            self.env["mail.activity"]
            .with_user(self.user_admin)
            .search(
                [
                    ("id", "in", self.test_activities.ids),
                    ("res_model", "=", self.test_lead_records._name),
                ]
            )
        )
        self.assertEqual(
            len(test_with_removed_as_admin),
            3,
            "With ACL check, activities linked to removed records are not kept is not assigned to the user",
        )

        self.env.invalidate_all()
        self.assertFalse(
            self.test_activities_removed.with_user(self.user_admin).has_access("read"),
            "No access to an activity linked to someone and whose record has been removed "
            "(considered as no access to record); and should not crash (no MissingError)",
        )
        with self.assertRaises(
            exceptions.AccessError
        ):  # should not raise a MissingError
            self.test_activities_removed.with_user(self.user_admin).read(["summary"])

        self.env.invalidate_all()
        test_with_removed = self.env["mail.activity"].search(
            [
                ("id", "in", self.test_activities.ids),
                ("res_model", "=", self.test_lead_records._name),
            ]
        )
        self.assertEqual(
            len(test_with_removed),
            4,
            "Even with ACL check, activities linked to removed records are kept if assigned to the user (see odoo/odoo#112126)",
        )

        # if not assigned -> should filter out
        self.env.invalidate_all()
        self.test_activities_removed.write({"user_id": self.user_admin.id})
        test_with_removed = self.env["mail.activity"].search(
            [
                ("id", "in", self.test_activities.ids),
                ("res_model", "=", self.test_lead_records._name),
            ]
        )
        self.assertEqual(
            len(test_with_removed),
            3,
            "With ACL check, activities linked to removed records are not kept if assigned to the another user",
        )
        self.test_activities_removed.write({"user_id": self.user_employee.id})

        # be sure activities on removed records do not crash when managed, and that
        # lost attachments are removed as well
        self.env.invalidate_all()
        lead_activities = self.test_lead_activities.with_user(self.user_employee)
        lead_act_attachments = self.lead_act_attachments.with_user(self.user_employee)
        self.assertEqual(
            len(lead_activities),
            4,
            "Simulate UI where activities are still displayed even if record removed",
        )
        self.assertEqual(
            len(lead_act_attachments),
            4,
            "Simulate UI where activities are still displayed even if record removed",
        )
        messages, _next_activities = lead_activities._action_done()
        self.assertEqual(
            len(messages), 3, "Should have posted one message / live record"
        )
        self.assertEqual(
            lead_activities.exists(),
            lead_activities - self.test_activities_removed,
            "Mark done should unlink activities linked to removed records",
        )
        self.assertEqual(lead_activities.exists().mapped("active"), [False] * 3)
        self.assertEqual(
            set(lead_act_attachments.exists().mapped("res_id")),
            set(messages.ids),
            "Mark done should clean up attachments linked to removed record, and linked other attachments to messages",
        )
        self.assertEqual(
            set(lead_act_attachments.exists().mapped("res_model")),
            set(["mail.message"] * 2),
        )

    @users("employee")
    def test_systray_activities_multi_company(self):
        """Explicitly check MC support, as well as allowed_company_ids, that
        limits visible records in a given session, should impact systray activities."""
        self.user_employee.write({"company_ids": [(4, self.company_2.id)]})

        self.authenticate(self.user_employee.login, self.user_employee.login)
        with freeze_time(self.dt_reference):
            groups_data = (
                self.call_jsonrpc(
                    "/mail/data", {"fetch_params": ["systray_get_activities"]}
                )
                .get("Store", {})
                .get("activityGroups", [])
            )

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            ("mail.activity", "Non accessible: deleted", (1, 1, 2, 0)),
            (self.test_record._name, "Archiving removes activities", (1, 1, 1, 0)),
            (
                self.test_lead_records._name,
                "Accessible (MC with all companies)",
                (1, 1, 2, 0),
            ),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(
                    values for values in groups_data if values["model"] == model_name
                )
                self.assertEqual(group_values["due_count"], exp_total)
                self.assertEqual(group_values["today_count"], exp_today)
                self.assertEqual(group_values["planned_count"], exp_planned)
                self.assertEqual(group_values["overdue_count"], exp_overdue)
                if (
                    model_name == "mail.activity"
                ):  # for mail.activity, there is a key with activities we can check
                    self.assertEqual(
                        sorted(group_values["activity_ids"]),
                        sorted(
                            (
                                self.test_activities_removed + self.test_activities_free
                            ).ids
                        ),
                    )

        # when allowed companies restrict visible records, linked activities are
        # removed from systray, considering you have to log into the right company
        # to see them (change in 18+)
        with freeze_time(self.dt_reference):
            groups_data = (
                self.call_jsonrpc(
                    "/mail/data",
                    {
                        "fetch_params": ["systray_get_activities"],
                        "context": {"allowed_company_ids": self.company_admin.ids},
                    },
                )
                .get("Store", {})
                .get("activityGroups", [])
            )

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            (
                "mail.activity",
                "Non accessible: deleted (MC ignored, stripped out like inaccessible records)",
                (1, 1, 2, 0),
            ),
            (self.test_record._name, "Archiving removes activities", (1, 1, 1, 0)),
            (self.test_lead_records._name, "Accessible", (1, 1, 1, 0)),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(
                    values for values in groups_data if values["model"] == model_name
                )
                self.assertEqual(group_values["due_count"], exp_total)
                self.assertEqual(group_values["today_count"], exp_today)
                self.assertEqual(group_values["planned_count"], exp_planned)
                self.assertEqual(group_values["overdue_count"], exp_overdue)
                if (
                    model_name == "mail.activity"
                ):  # for mail.activity, there is a key with activities we can check
                    self.assertEqual(
                        sorted(group_values["activity_ids"]),
                        sorted(
                            (
                                self.test_activities_removed + self.test_activities_free
                            ).ids
                        ),
                    )

        # now not having accessible to company 2 records: tread like forbidden
        self.user_employee.write({"company_ids": [(3, self.company_2.id)]})
        with freeze_time(self.dt_reference):
            groups_data = (
                self.call_jsonrpc(
                    "/mail/data",
                    {
                        "fetch_params": ["systray_get_activities"],
                        "context": {"allowed_company_ids": self.company_admin.ids},
                    },
                )
                .get("Store", {})
                .get("activityGroups", [])
            )

        for model_name, msg, (exp_total, exp_today, exp_planned, exp_overdue) in [
            (
                "mail.activity",
                "Non accessible: deleted + company error managed like forbidden record",
                (1, 1, 3, 0),
            ),
            (self.test_record._name, "Archiving removes activities", (1, 1, 1, 0)),
            (self.test_lead_records._name, "Accessible", (1, 1, 1, 0)),
        ]:
            with self.subTest(model_name=model_name, msg=msg):
                group_values = next(
                    values for values in groups_data if values["model"] == model_name
                )
                self.assertEqual(group_values["due_count"], exp_total)
                self.assertEqual(group_values["today_count"], exp_today)
                self.assertEqual(group_values["planned_count"], exp_planned)
                self.assertEqual(group_values["overdue_count"], exp_overdue)
                if (
                    model_name == "mail.activity"
                ):  # for mail.activity, there is a key with activities we can check
                    self.assertEqual(
                        sorted(group_values["activity_ids"]),
                        sorted(
                            (
                                self.test_activities_removed
                                + self.test_activities_company_2
                                + self.test_activities_free
                            ).ids
                        ),
                    )


@tests.tagged("mail_activity")
@freeze_time("2024-01-01 09:00:00")
class TestActivitySystrayBusNotify(TestActivityCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee_2 = cls.user_employee.copy(
            default={
                "login": "employee_2",
                "email": "user_employee_2@test.lan",
                "notification_type": "email",
            }
        )

        cls.activity_vals = [
            {
                "res_model_id": cls.env["ir.model"]._get_id(cls.test_record._name),
                "res_id": cls.test_record.id,
                "date_deadline": dt,
                "user_id": cls.user_employee.id,
            }
            | extra
            for dt, extra in zip(
                (
                    datetime(2023, 12, 31, 15, 0, 0),
                    datetime(2023, 12, 31, 15, 0, 0),
                    datetime(2024, 1, 1, 15, 0, 0),
                    datetime(2024, 1, 2, 15, 0, 0),
                ),
                ({"active": False}, {}, {}, {}),
                strict=True,
            )
        ]

    def _systray_counter(self, user):
        """The number the systray badge shows on a reload, for `user`."""
        groups = self.env["res.users"].with_user(user)._get_activity_groups()
        return sum(group.get("due_count", 0) for group in groups)

    def _expect_employee_diff(self, count_diff):
        """One expected bus notification on the employee's channel."""
        partner = self.user_employee.partner_id
        return [
            (
                [(self.env.cr.dbname, partner._name, partner.id)],
                [
                    {
                        "type": "mail.activity/updated",
                        "payload": {
                            "count_diff": count_diff,
                        }
                        | (
                            {"activity_created": True}
                            if count_diff > 0
                            else {"activity_deleted": True}
                        ),
                    }
                ],
            )
        ]

    @users("employee")
    def test_notify_create_unlink_activities(self):
        """Creating and unlinking activities notifies the change in "to be done"
        count per user -- counted in the same unit as the badge it adjusts.

        ``activity_vals`` puts all four activities on ONE record, of which two
        are to-do. ``_get_activity_groups`` counts one unit per *record* holding
        at least one to-do activity, so the delta is 1, not 2: the counter used
        to be seeded in records and moved in activities, and a client that saw
        +2 here dropped back to 1 as soon as the systray was opened.
        """
        users = self.env.user + self.user_employee_2

        expected_create_notifs = [
            (
                [(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)],
                [
                    {
                        "type": "mail.activity/updated",
                        "payload": {
                            "activity_created": True,
                            "count_diff": 1,
                        },
                    }
                ],
            )
            for user in users
        ]
        expected_unlink_notifs = [
            (
                [(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)],
                [
                    {
                        "type": "mail.activity/updated",
                        "payload": {
                            "activity_deleted": True,
                            "count_diff": -1,
                        },
                    }
                ],
            )
            for user in users
        ]
        for (
            user,
            (expected_create_notif_channels, expected_create_notif_message_items),
            (expected_unlink_notif_channels, expected_unlink_notif_message_items),
        ) in zip(users, expected_create_notifs, expected_unlink_notifs, strict=True):
            user_activity_vals = [
                vals | {"user_id": user.id} for vals in self.activity_vals
            ]
            before = self._systray_counter(user)
            with self.assertBus(
                expected_create_notif_channels, expected_create_notif_message_items
            ):
                activities = self.env["mail.activity"].create(user_activity_vals)
            # the invariant the payload exists to preserve: applying the delta to
            # the badge lands on the value a reload would compute
            self.assertEqual(self._systray_counter(user), before + 1)
            with self.assertBus(
                expected_unlink_notif_channels, expected_unlink_notif_message_items
            ):
                activities.unlink()
            self.assertEqual(self._systray_counter(user), before)

    @users("employee")
    def test_notify_counts_records_not_activities(self):
        """Two activities on one record are one unit; on two records, two."""
        model_id = self.env["ir.model"]._get_id(self.test_record._name)
        record_2 = self.env["mail.test.activity"].sudo().create({"name": "second"})
        base = {
            "res_model_id": model_id,
            "date_deadline": datetime(2023, 12, 31, 15, 0, 0),
            "user_id": self.env.user.id,
        }
        channel = [
            (
                self.env.cr.dbname,
                self.env.user.partner_id._name,
                self.env.user.partner_id.id,
            )
        ]

        with self.assertBus(
            channel,
            [
                {
                    "type": "mail.activity/updated",
                    "payload": {"activity_created": True, "count_diff": 1},
                }
            ],
        ):
            same_record = self.env["mail.activity"].create(
                [
                    base | {"res_id": self.test_record.id},
                    base | {"res_id": self.test_record.id},
                ]
            )
        self.assertEqual(self._systray_counter(self.env.user), 1)

        # a third activity on the same record moves nothing: the record already counts
        self._reset_bus()
        third = self.env["mail.activity"].create(base | {"res_id": self.test_record.id})
        self.assertBusNotifications([], [])
        self.assertEqual(self._systray_counter(self.env.user), 1)

        # one on another record does move it
        self._reset_bus()
        with self.assertBus(
            channel,
            [
                {
                    "type": "mail.activity/updated",
                    "payload": {"activity_created": True, "count_diff": 1},
                }
            ],
        ):
            other_record = self.env["mail.activity"].create(
                base | {"res_id": record_2.id}
            )
        self.assertEqual(self._systray_counter(self.env.user), 2)

        # removing one of three leaves the record counted -> no notification,
        # where a per-activity delta would have wrongly decremented the badge
        self._reset_bus()
        third.unlink()
        self.assertBusNotifications([], [])
        self.assertEqual(self._systray_counter(self.env.user), 2)

        (same_record + other_record).unlink()
        self.assertEqual(self._systray_counter(self.env.user), 0)

    @users("employee")
    def test_notify_counts_in_the_assignee_timezone(self):
        """The delta is decided on the assignee's own today, like ``state``.

        Frozen at 2024-01-01 09:00 UTC. For an assignee at UTC-11 it is still
        2023-12-31 there, so an activity due on the 1st is *planned* for them and
        the badge must not count it. Deciding on the server's date instead --
        ``date_deadline <= fields.Date.today()``, which is what create, write and
        unlink used to do -- would have pushed +1 against a badge that computes 0
        on reload, because the badge is built from ``state`` and ``state`` has
        always answered in the assignee's timezone.
        """
        self.env.user.tz = "Pacific/Midway"  # UTC-11
        Activity = self.env["mail.activity"]
        self.assertEqual(Activity._today_in_tz(self.env.user.tz), date(2023, 12, 31))
        self.assertEqual(
            Activity.with_context(tz=False)._today_in_tz(False), date(2024, 1, 1)
        )
        vals = {
            "res_model_id": self.env["ir.model"]._get_id(self.test_record._name),
            "res_id": self.test_record.id,
            "user_id": self.env.user.id,
        }

        self._reset_bus()
        planned = Activity.create(
            vals | {"date_deadline": datetime(2024, 1, 1, 15, 0, 0)}
        )
        self.assertEqual(
            planned.state, "planned", "today on the server, tomorrow for the assignee"
        )
        self.assertBusNotifications([], [])
        self.assertEqual(self._systray_counter(self.env.user), 0)

        # their own today does count
        channel = [
            (
                self.env.cr.dbname,
                self.env.user.partner_id._name,
                self.env.user.partner_id.id,
            )
        ]
        with self.assertBus(
            channel,
            [
                {
                    "type": "mail.activity/updated",
                    "payload": {"activity_created": True, "count_diff": 1},
                }
            ],
        ):
            due = Activity.create(
                vals | {"date_deadline": datetime(2023, 12, 31, 15, 0, 0)}
            )
        self.assertEqual(due.state, "today")
        self.assertEqual(self._systray_counter(self.env.user), 1)

    @users("employee")
    def test_notify_update_activities(self):
        write_vals_all = [
            # added to counter for employee 2, removed from counter for current employee
            {"user_id": self.user_employee_2.id},
            {
                "user_id": self.user_employee_2.id,
                "date_deadline": datetime(2023, 12, 31, 15, 0, 0),
                "active": True,
            },
            # just notify
            {
                "date_deadline": datetime(2024, 1, 2, 15, 0, 0)
            },  # everything is in the future -> all removed from counter
            {
                "date_deadline": datetime(2023, 12, 31, 15, 0, 0)
            },  # everything is in the past -> the one from the future is added
            {"active": False},  # everything is archived -> all removed from counter
            {"active": True},  # the archived one is unarchived -> added to counter
            {},  # no "to be done" count change -> no notif
            [
                {"date_deadline": datetime(2024, 1, 2, 15, 0, 0), "active": True},
                {},
                {},
                {},
            ],
        ]

        # All four activities sit on ONE record, so the counter moves by at most
        # one unit per user: what changes is whether that record still carries a
        # to-do activity, not how many it carries.
        expected_notifs = [
            # transfer to the second employee: the record leaves one counter and
            # joins the other
            [
                (
                    [(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)],
                    [
                        {
                            "type": "mail.activity/updated",
                            "payload": {
                                "count_diff": count_diff,
                            }
                            | (
                                {"activity_created": True}
                                if count_diff > 0
                                else {"activity_deleted": True}
                            ),
                        }
                    ],
                )
                for user, count_diff in zip(
                    self.user_employee + self.user_employee_2, [-1, 1], strict=True
                )
            ],
            # same transfer, also pulling every deadline into the past: still one
            # record either side
            [
                (
                    [(self.env.cr.dbname, user.partner_id._name, user.partner_id.id)],
                    [
                        {
                            "type": "mail.activity/updated",
                            "payload": {
                                "count_diff": count_diff,
                            }
                            | (
                                {"activity_created": True}
                                if count_diff > 0
                                else {"activity_deleted": True}
                            ),
                        }
                    ],
                )
                for user, count_diff in zip(
                    self.user_employee + self.user_employee_2, [-1, 1], strict=True
                )
            ],
        ] + [
            # every deadline in the future -> the record stops counting
            self._expect_employee_diff(-1),
            # every deadline in the past: the record already counted (the active
            # past one, and today's) and still does -> nothing to say
            [([], [])],
            # everything archived -> the record stops counting
            self._expect_employee_diff(-1),
            # unarchiving adds a third to-do activity to a record that already
            # counts -> nothing to say
            [([], [])],
            [([], [])],  # no change -> no notif
            [([], [])],  # no change in "todo" count -> no notif
        ]
        for write_vals, expected_notif_vals in zip(
            write_vals_all, expected_notifs, strict=True
        ):
            with self.subTest(vals=write_vals):
                _past_archived, _past_active, _today, _tomorrow = activities = self.env[
                    "mail.activity"
                ].create(self.activity_vals)
                self._reset_bus()
                if isinstance(write_vals, list):
                    for activity, vals in zip(activities, write_vals, strict=True):
                        activity.write(vals)
                else:
                    activities.write(write_vals)
                for notif_channels, notif_messages in expected_notif_vals:
                    self.assertBusNotifications(notif_channels, notif_messages)
                activities.unlink()


@tests.tagged("mail_activity")
class TestActivityViewHelpers(TestActivityCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.type_todo = cls.env.ref("test_mail.mail_act_test_todo")
        cls.type_call = cls.env.ref("test_mail.mail_act_test_call")
        cls.type_upload = cls.env.ref("test_mail.mail_act_test_upload_document")

        cls.user_employee_2 = mail_new_test_user(
            cls.env,
            name="Employee2",
            login="employee2",
        )
        cls.attachment_1, cls.attachment_2 = cls.env["ir.attachment"].create(
            [
                {
                    "name": f"Uploaded doc_{idx + 1}",
                    "raw": b"bar",
                    "res_model": cls.test_record_2._name,
                    "res_id": cls.test_record_2.id,
                }
                for idx in range(2)
            ]
        )
        cls.user_employee.tz = cls.user_admin.tz

    @freeze_time("2023-10-18 06:00:00")
    def test_get_activity_data(self):
        get_activity_data = self.env["mail.activity"].get_activity_data

        with self.with_user("employee"):
            # Setup activities: 3 for the first record, 2 "done" and 2 ongoing for the second
            test_record, test_record_2 = self.env["mail.test.activity"].browse(
                (self.test_record + self.test_record_2).ids
            )
            now_utc = datetime.now(UTC)
            now_user = now_utc.astimezone(timezone(self.env.user.tz or "UTC"))
            today_user = now_user.date()

            for days, user_id in (
                (-1, self.user_employee_2),
                (0, self.user_employee),
                (1, self.user_admin),
            ):
                test_record.activity_schedule(
                    "test_mail.mail_act_test_upload_document",
                    today_user + relativedelta(days=days),
                    user_id=user_id.id,
                )
            for days, user_id in (
                (-2, self.user_admin),
                (0, self.user_employee),
                (2, self.user_employee_2),
                (3, self.user_admin),
                (4, self.env["res.users"]),
            ):
                test_record_2.activity_schedule(
                    "test_mail.mail_act_test_upload_document",
                    today_user + relativedelta(days=days),
                    user_id=user_id.id,
                )
            record_activities = test_record.activity_ids
            record_2_activities = test_record_2.activity_ids
            record_2_activities[0].action_feedback(
                feedback="Done", attachment_ids=self.attachment_1.ids
            )
            record_2_activities[1].action_feedback(
                feedback="Done", attachment_ids=self.attachment_2.ids
            )

            # Check get activity data
            activity_data = get_activity_data(
                "mail.test.activity", None, fetch_done=True
            )
            self.assertEqual(
                activity_data["activity_res_ids"], [test_record.id, test_record_2.id]
            )
            self.assertDictEqual(
                next(
                    (
                        t
                        for t in activity_data["activity_types"]
                        if t["id"] == self.type_upload.id
                    ),
                    {},
                ),
                {
                    "id": self.type_upload.id,
                    "name": "Document",
                    "template_ids": [],
                },
            )

            grouped = activity_data["grouped_activities"][test_record.id][
                self.type_upload.id
            ]
            grouped["ids"] = set(grouped["ids"])  # ids order doesn't matter
            self.assertDictEqual(
                grouped,
                {
                    "state": "overdue",
                    "count_by_state": {"overdue": 1, "planned": 1, "today": 1},
                    "ids": set(record_activities.ids),
                    "reporting_date": record_activities[0].date_deadline,
                    "user_assigned_ids": record_activities.user_id.ids,
                    "summaries": [act.summary for act in record_activities],
                },
            )

            grouped = activity_data["grouped_activities"][test_record_2.id][
                self.type_upload.id
            ]
            grouped["ids"] = set(grouped["ids"])
            self.assertDictEqual(
                grouped,
                {
                    "state": "planned",
                    "count_by_state": {"done": 2, "planned": 3},  # free user is planned
                    "ids": set(record_2_activities.ids),
                    "reporting_date": record_2_activities[2].date_deadline,
                    "user_assigned_ids": record_2_activities[2:].user_id.ids,
                    "attachments_info": {
                        "count": 2,
                        "most_recent_id": self.attachment_2.id,
                        "most_recent_name": "Uploaded doc_2",
                    },
                    "summaries": [act.summary for act in record_2_activities],
                },
            )

            # Mark all first record activities as "done" and check activity data
            record_activities.action_feedback(
                feedback="Done", attachment_ids=self.attachment_1.ids
            )
            self.assertEqual(
                record_activities[2].date_done, date.today()
            )  # Thanks to freeze_time
            # Each message owns its own copy; the newest is the last one made.
            most_recent_attachment_id = max(record_activities.attachment_ids.ids)
            activity_data = get_activity_data(
                "mail.test.activity", None, fetch_done=True
            )
            grouped = activity_data["grouped_activities"][test_record.id][
                self.type_upload.id
            ]
            grouped["ids"] = set(grouped["ids"])
            self.assertDictEqual(
                grouped,
                {
                    "state": "done",
                    "count_by_state": {"done": 3},
                    "ids": set(record_activities.ids),
                    "reporting_date": record_activities[2].date_done,
                    "user_assigned_ids": [],
                    "attachments_info": {
                        # One per message: `_action_done` copies a shared attachment
                        # rather than letting three messages point at one record that
                        # only the first of them owns.
                        "count": 3,
                        "most_recent_id": most_recent_attachment_id,
                        "most_recent_name": self.attachment_1.name,
                    },
                    "summaries": [act.summary for act in record_activities],
                },
            )
            self.assertEqual(
                activity_data["activity_res_ids"], [test_record_2.id, test_record.id]
            )

            # Check filters (domain, pagination and fetch_done)
            self.assertEqual(
                get_activity_data(
                    "mail.test.activity",
                    domain=[("id", "in", test_record.ids)],
                    fetch_done=True,
                )["activity_res_ids"],
                [test_record.id],
            )
            self.assertEqual(
                get_activity_data("mail.test.activity", None, fetch_done=False)[
                    "activity_res_ids"
                ],
                [test_record_2.id],
            )
            # Note that the records are ordered by ids not by deadline (so we get the "wrong" order)
            self.assertEqual(
                get_activity_data(
                    "mail.test.activity", None, offset=1, fetch_done=True
                )["activity_res_ids"],
                [test_record_2.id],
            )
            self.assertEqual(
                get_activity_data("mail.test.activity", None, limit=1, fetch_done=True)[
                    "activity_res_ids"
                ],
                [test_record.id],
            )

            # Unarchiving activities should restore the activity
            record_activities.action_unarchive()
            self.assertFalse(any(act.date_done for act in record_activities))
            self.assertTrue(all(act.date_deadline for act in record_activities))
            activity_data = get_activity_data(
                "mail.test.activity", None, fetch_done=True
            )
            grouped = activity_data["grouped_activities"][test_record.id][
                self.type_upload.id
            ]
            self.assertEqual(grouped["state"], "overdue")
            self.assertEqual(
                grouped["count_by_state"], {"overdue": 1, "planned": 1, "today": 1}
            )
            self.assertEqual(
                grouped["reporting_date"], record_activities[0].date_deadline
            )
            self.assertEqual(
                activity_data["activity_res_ids"], [test_record.id, test_record_2.id]
            )
            grouped["ids"] = set(grouped["ids"])
            self.assertDictEqual(
                grouped,
                {
                    "state": "overdue",
                    "count_by_state": {"overdue": 1, "planned": 1, "today": 1},
                    "ids": set(record_activities.ids),
                    "reporting_date": record_activities[0].date_deadline,
                    "user_assigned_ids": record_activities.user_id.ids,
                    "summaries": [act.summary for act in record_activities],
                },
            )


@tests.tagged("post_install", "-at_install")
class TestTours(HttpCase):
    def test_activity_view_data_with_offset(self):
        self.patch(MailTestActivity, "_order", "date desc, id desc")
        MailTestActivityModel = self.env["mail.test.activity"]
        MailTestActivityCtx = MailTestActivityModel.with_context({"lang": "en_US"})
        MailTestActivityModel.create(
            {
                "date": "2021-05-02",
                "name": "Task 1",
            }
        ).activity_schedule(
            "test_mail.mail_act_test_todo",
            summary="Activity 1",
            date_deadline=fields.Date.context_today(MailTestActivityCtx)
            - timedelta(days=7),
            user_id=self.env.uid,
        )
        MailTestActivityModel.create(
            {
                "date": "2021-05-16",
                "name": "Task 1 without activity",
            }
        )
        MailTestActivityModel.create(
            {
                "date": "2021-05-09",
                "name": "Task 2",
            }
        ).activity_schedule(
            "test_mail.mail_act_test_todo",
            summary="Activity 2",
            date_deadline=fields.Date.context_today(MailTestActivityCtx),
            user_id=self.env.uid,
        )
        MailTestActivityModel.create(
            {
                "date": "2021-05-16",
                "name": "Task 3",
            }
        ).activity_schedule(
            "test_mail.mail_act_test_todo",
            summary="Activity 3",
            date_deadline=fields.Date.context_today(MailTestActivityCtx)
            + timedelta(days=7),
            user_id=self.env.uid,
        )
        MailTestActivityModel.create(
            {
                "date": "2021-05-16",
                "name": "Task 2 without activity",
            }
        )

        self.env["ir.ui.view"].create(
            {
                "name": "Test Activity View",
                "model": "mail.test.activity",
                "type": "activity",
                "arch": """
                <activity string="OrderedMailTestActivity">
                    <templates>
                        <div t-name="activity-box">
                            <field name="name"/>
                        </div>
                    </templates>
                </activity>
            """,
            }
        )
        self.start_tour(
            "/odoo?debug=1",
            "mail_activity_view",
            login="admin",
        )


@tests.tagged("post_install", "-at_install")
class TestActivityResName(ActivityScheduleCase):
    """``res_name`` resolves the linked document without probing for it.

    The probe (``exists()``) used to run on every read -- including every
    notification template that renders ``res_name`` -- to guard a state that
    only arises when a record is cascade-deleted in the database, skipping the
    unlink override that would have removed its activities.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.activity = cls.env["mail.activity"].create(
            {
                "activity_type_id": cls.env.ref("mail.mail_activity_data_todo").id,
                "res_id": cls.record.id,
                "res_model_id": cls.env.ref("test_mail.model_mail_test_activity").id,
                "summary": "Act",
            }
        )

    def _recompute_res_name(self):
        self.env.invalidate_all()
        self.env["mail.activity"].browse(self.activity.id)._compute_res_name()
        return self.activity.res_name

    def test_res_name_follows_the_document(self):
        self.assertEqual(self._recompute_res_name(), "Doc")
        self.record.name = "Renamed"
        self.assertEqual(self._recompute_res_name(), "Renamed")

    def test_res_name_costs_one_query_for_the_document(self):
        """The happy path reads the document; it must not also probe for it."""
        self.env.invalidate_all()
        activity = self.env["mail.activity"].browse(self.activity.id)
        with self.assertQueryCount(__system__=2):
            activity._compute_res_name()

    def test_cascade_deleted_document_leaves_a_blank_name(self):
        """The row is removed behind the ORM's back, as a DB-level cascade does."""
        self.env.cr.execute(
            "DELETE FROM mail_test_activity WHERE id = %s", (self.record.id,)
        )
        self.assertFalse(self._recompute_res_name())

    def test_one_missing_document_does_not_blank_its_siblings(self):
        survivor = self.env["mail.test.activity"].create({"name": "Survivor"})
        sibling = self.env["mail.activity"].create(
            {
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "res_id": survivor.id,
                "res_model_id": self.env.ref("test_mail.model_mail_test_activity").id,
                "summary": "Act 2",
            }
        )
        self.env.cr.execute(
            "DELETE FROM mail_test_activity WHERE id = %s", (self.record.id,)
        )
        self.env.invalidate_all()
        (self.activity + sibling)._compute_res_name()
        self.assertFalse(self.activity.res_name)
        self.assertEqual(sibling.res_name, "Survivor")


@tests.tagged("mail_activity")
class TestActivityAccessAndState(ActivityScheduleCase):
    """Access, cache and idempotence properties of mail.activity."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.other_user = mail_new_test_user(
            cls.env,
            name="Colleague",
            login="colleague",
            groups="base.group_user",
        )

    def _new_activity(self, **vals):
        return self.env["mail.activity"].create(
            {
                "res_model_id": self.model_id,
                "res_id": self.record.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                **vals,
            }
        )

    def test_can_write_is_per_reader(self):
        """``can_write`` answers for the reader, whichever identity read first.

        It is a pure function of ``env.uid`` and ships to the client in
        ``_to_store_defaults``, where it decides which buttons the chatter draws.
        Without ``@api.depends_context("uid")`` its cache key was ``()``, so one
        slot was shared by every environment in the transaction and a ``sudo()``
        read anywhere earlier in the request handed its own verdict to the user.
        """
        activity = self._new_activity(user_id=self.user_admin.id)
        self.env.flush_all()
        self.assertIn(
            "uid",
            self.env.registry.field_depends_context[
                self.env["mail.activity"]._fields["can_write"]
            ],
        )

        as_employee = activity.with_user(self.user_employee)
        self.env.invalidate_all()
        employee_verdict = as_employee.can_write
        self.env.invalidate_all()
        sudo_verdict = activity.sudo().can_write
        self.assertTrue(sudo_verdict, "the superuser may always write")

        # whichever order they are read in, each identity gets its own answer
        self.env.invalidate_all()
        self.assertEqual(activity.sudo().can_write, sudo_verdict)
        self.assertEqual(as_employee.can_write, employee_verdict)
        self.env.invalidate_all()
        self.assertEqual(as_employee.can_write, employee_verdict)
        self.assertEqual(activity.sudo().can_write, sudo_verdict)

    def test_can_write_reaches_the_client_per_reader(self):
        """The same, through the RPC the chatter popover actually calls."""
        activity = self._new_activity(user_id=self.user_admin.id)
        self.env.flush_all()
        as_employee = activity.with_user(self.user_employee)

        self.env.invalidate_all()
        clean = as_employee.activity_format()["mail.activity"][0]["can_write"]
        self.env.invalidate_all()
        activity.sudo().can_write  # any sudo() touch earlier in the request
        polluted = as_employee.activity_format()["mail.activity"][0]["can_write"]
        self.assertEqual(clean, polluted)

    def test_schedule_for_another_user_on_a_read_post_document(self):
        """A read-only document that opts into ``_mail_post_access = 'read'``
        accepts an activity scheduled for somebody else.

        ``_check_access`` states create access as "``mail_post_access`` on the
        related document", and posting a message on such a record works. The
        follower side effect used the public ``message_subscribe``, which
        re-checks *write* for any partner but the caller's own, so a user could
        schedule for themselves and not for a colleague -- failing with an
        AccessError naming the document.
        """
        record = self.env["mail.test.container"].create({"name": "Read-post doc"})
        self.assertEqual(record._mail_post_access, "read")
        model_id = self.env["ir.model"]._get_id(record._name)
        as_employee = record.with_user(self.user_employee)
        self.assertTrue(as_employee.has_access("read"))

        # the policy the model states, exercised directly
        as_employee.message_post(
            body="hello", message_type="comment", subtype_xmlid="mail.mt_comment"
        )

        with self.with_user("employee"):
            Activity = self.env["mail.activity"]
            for assignee, label in (
                (self.env.user, "themselves"),
                (self.other_user, "a colleague"),
            ):
                with self.subTest(assignee=label):
                    activity = Activity.create(
                        {
                            "res_model_id": model_id,
                            "res_id": record.id,
                            "user_id": assignee.id,
                            "summary": f"for {label}",
                        }
                    )
                    self.assertEqual(activity.user_id, assignee)
            # and reassigning one is the same operation from the other side
            mine = Activity.search(
                [("res_id", "=", record.id), ("user_id", "=", self.env.uid)], limit=1
            )
            mine.write({"user_id": self.other_user.id})
            self.assertEqual(mine.user_id, self.other_user)

    def test_action_feedback_is_not_replayed(self):
        """Marking a done activity done again neither posts nor rewrites.

        ``action_done`` filtered on ``active``; ``action_feedback`` -- the public
        API, and the one the web client calls without disabling its button while
        the RPC is in flight -- did not, so a double click posted a second "done"
        message and overwrote the feedback.
        """
        activity = self._new_activity(user_id=self.env.uid, summary="Once")
        self.env.flush_all()
        activity.action_feedback(feedback="first")
        self.env.flush_all()
        messages = self.record.message_ids
        date_done = activity.date_done

        activity.action_feedback(feedback="second")
        self.env.flush_all()
        self.assertEqual(self.record.message_ids, messages, "no second done message")
        self.assertEqual(activity.feedback, "first", "the first feedback stands")
        self.assertEqual(activity.date_done, date_done)

    def test_feedback_and_archive_are_one_write(self):
        """Marking done writes once, not once to archive and once for feedback."""
        activities = self.env["mail.activity"].create(
            [
                {
                    "res_model_id": self.model_id,
                    "res_id": self.record.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "user_id": self.env.uid,
                    "summary": f"act {idx}",
                }
                for idx in range(3)
            ]
        )
        self.env.flush_all()

        writes = []
        origin = type(self.env["mail.activity"]).write

        def counting_write(records, vals):
            writes.append(sorted(vals))
            return origin(records, vals)

        with patch.object(type(self.env["mail.activity"]), "write", counting_write):
            activities.action_feedback(feedback="done")
        self.assertEqual(writes, [["active", "feedback"]])

    def test_state_survives_a_missing_deadline(self):
        """``state`` is assigned even with no deadline, as onchange can produce."""
        virtual = self.env["mail.activity"].new(
            {
                "res_model_id": self.model_id,
                "res_id": self.record.id,
                "user_id": self.env.uid,
            }
        )
        virtual.date_deadline = False
        self.assertFalse(virtual.state)

    def test_date_done_is_the_assignee_date(self):
        """``date_done`` records the assignee's own day, not the server's UTC one."""
        user_ahead = mail_new_test_user(
            self.env,
            name="Ahead",
            login="ahead",
            groups="base.group_user",
            tz="Pacific/Kiritimati",  # UTC+14
        )
        activity = self._new_activity(user_id=user_ahead.id)
        self.env.flush_all()
        with freeze_time("2024-01-01 15:00:00"):  # 2024-01-02 05:00 for the assignee
            activity.action_archive()
            self.env.flush_all()
            self.assertEqual(activity.date_done, date(2024, 1, 2))

    def test_action_cancel_unlinks_once(self):
        activities = self.env["mail.activity"].create(
            [
                {
                    "res_model_id": self.model_id,
                    "res_id": self.record.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "user_id": self.env.uid,
                    "summary": f"act {idx}",
                }
                for idx in range(5)
            ]
        )
        self.env.flush_all()

        calls = []
        origin = type(self.env["mail.activity"]).unlink

        def counting_unlink(records):
            calls.append(len(records))
            return origin(records)

        with patch.object(type(self.env["mail.activity"]), "unlink", counting_unlink):
            activities.action_cancel()
        # empty calls come from cascades; what matters is that the five records
        # are removed by one call and not one call each
        self.assertEqual([count for count in calls if count], [5])
        self.assertFalse(activities.exists())

    def test_activity_on_a_model_without_a_chatter(self):
        """A model with no followers still carries activities, it just gets no
        chatter side effect.

        ``res_model_id`` is a plain m2o to ir.model -- only the activity *type*
        restricts itself to ``is_mail_thread`` -- so an activity may sit on a
        model that has neither ``_message_subscribe`` nor
        ``message_post_with_source``. Scheduling one for somebody else used to
        die on the first and marking it done would have died on the second.
        """
        target = self.env["res.users"]
        self.assertFalse(
            hasattr(target, "_message_subscribe"),
            "the vehicle for this test must really lack a chatter",
        )
        activity = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id(target._name),
                "res_id": self.user_admin.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": self.other_user.id,
                "summary": "no chatter here",
            }
        )
        self.env.flush_all()
        self.assertEqual(activity.user_id, self.other_user)

        # reassignment goes through the same side effect
        activity.write({"user_id": self.user_employee.id})
        self.assertEqual(activity.user_id, self.user_employee)

        # and so does notifying, and marking done
        activity.action_notify()
        messages, _next = activity._action_done(feedback="done")
        self.assertFalse(messages, "nowhere to post it")
        self.assertFalse(activity.active)
        self.assertEqual(activity.feedback, "done")

    def test_feedback_schedule_next_wants_one_activity(self):
        activities = self.env["mail.activity"].create(
            [
                {
                    "res_model_id": self.model_id,
                    "res_id": self.record.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "user_id": self.env.uid,
                    "summary": f"act {idx}",
                }
                for idx in range(2)
            ]
        )
        with self.assertRaises(ValueError):
            activities.action_feedback_schedule_next()


@tests.tagged("mail_activity")
class TestActivitySearchPaging(ActivityScheduleCase):
    """``_search`` filters access in Python; pagination must survive that."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.activities = cls.env["mail.activity"].create(
            [
                {
                    "res_model_id": cls.env["ir.model"]._get_id("mail.test.activity"),
                    "res_id": cls.record.id,
                    "activity_type_id": cls.env.ref("mail.mail_activity_data_todo").id,
                    "user_id": cls.user_employee.id,
                    "summary": f"act {idx:02d}",
                    "date_deadline": date(2024, 1, 1) + timedelta(days=idx),
                }
                for idx in range(25)
            ]
        )

    def test_pages_are_full_and_contiguous(self):
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        domain = [("id", "in", self.activities.ids)]
        order = "date_deadline ASC, id ASC"
        everything = Activity.search(domain, order=order)
        self.assertEqual(len(everything), 25)

        for size in (1, 4, 10):
            with self.subTest(page_size=size):
                paged = self.env["mail.activity"]
                for offset in range(0, 25, size):
                    page = Activity.search(
                        domain, offset=offset, limit=size, order=order
                    )
                    self.assertLessEqual(len(page), size)
                    paged |= page
                    self.assertEqual(
                        page.ids,
                        everything[offset : offset + size].ids,
                        "each page holds exactly the slice of the full result",
                    )
                self.assertEqual(paged.ids, everything.ids)

    def test_a_limit_of_zero_asks_for_no_rows(self):
        """``limit=0`` means zero rows, not "no limit".

        `Query` emits the clause on `limit is not None` and `test_query` pins
        `search_count(limit=0) == 0`, so a scan that read 0 as "unbounded"
        answered every row where every other model answers none.
        """
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        domain = [("id", "in", self.activities.ids)]
        self.assertFalse(Activity.search(domain, limit=0))
        self.assertEqual(Activity.search_count(domain, limit=0), 0)
        self.assertFalse(
            Activity.sudo().search(domain, limit=0),
            "and the superuser branch agrees",
        )

    def test_no_limit_means_every_row(self):
        """The other half of the same contract: `None` is the unbounded one."""
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        domain = [("id", "in", self.activities.ids)]
        self.assertEqual(len(Activity.search(domain)), 25)
        self.assertEqual(Activity.search_count(domain), 25)
        self.assertEqual(len(Activity.sudo().search(domain, limit=None)), 25)

    def test_every_spelling_of_a_limit_agrees_with_a_plain_model(self):
        """`_search` admits four spellings and they are not interchangeable.

        `orm/models/mixins/_query.py` reads them as: None and False unbounded,
        True as 1, 0 as zero rows. `False == 0` is True in Python, so a scan
        that tests either truthiness or `== 0` collapses the two and answers
        nothing for the one that means everything. Compared against a model
        with no `_search` override rather than against a hardcoded expectation,
        so the contract is read off the ORM and not restated here.
        """
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        Control = self.env["res.partner"].with_user(self.user_employee)
        domain = [("id", "in", self.activities.ids)]
        self.assertFalse(
            Activity._domain_is_mine(domain), "this must exercise the scan path"
        )
        total = len(Activity.search(domain))
        self.assertEqual(total, 25)
        control_total = Control.search_count([])
        self.assertTrue(control_total, "the control needs rows to be a control")

        for limit, expected in (
            (None, total),
            (False, total),
            (True, 1),
            (0, 0),
            (4, 4),
        ):
            with self.subTest(limit=limit):
                control = len(Control.search([], limit=limit))
                self.assertEqual(
                    control,
                    min(expected, control_total) if expected else expected,
                    "the control model defines the contract",
                )
                self.assertEqual(len(Activity.search(domain, limit=limit)), expected)
                self.assertEqual(
                    len(Activity.sudo().search(domain, limit=limit)),
                    expected,
                    "and the superuser branch agrees",
                )

    def test_inaccessible_activities_do_not_shorten_a_page(self):
        """A page is filled with accessible rows, not truncated by hidden ones."""
        # Activities attached to no document are readable by their assignee
        # alone, so these are invisible to the employee whatever they can read.
        hidden = self.env["mail.activity"].create(
            [
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "user_id": self.user_admin.id,
                    "summary": f"hidden {idx}",
                    "date_deadline": date(2024, 1, 1),
                }
                for idx in range(10)
            ]
        )
        self.env.flush_all()

        Activity = self.env["mail.activity"].with_user(self.user_employee)
        domain = [("id", "in", (self.activities + hidden).ids)]
        visible = Activity.search(domain)
        self.assertFalse(
            visible & hidden.with_user(self.user_employee),
            "the employee is not the assignee of the hidden ones",
        )
        page = Activity.search(domain, limit=5, order="date_deadline ASC, id ASC")
        self.assertEqual(len(page), 5, "the page is full despite the hidden rows")
        self.assertEqual(page.ids, visible[:5].ids)


@tests.tagged("mail_activity")
class TestActivityGarbageCollect(ActivityScheduleCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")

    def setUp(self):
        super().setUp()
        # ir.config_parameter reads go through an ormcache the transaction
        # rollback does not clear, so state both knobs explicitly per test.
        for parameter in ("delete_overdue_years", "delete_done_years"):
            self.env["ir.config_parameter"].sudo().set_param(
                f"mail.activity.gc.{parameter}", "0"
            )

    def _activity(self, deadline, done=False):
        activity = self.env["mail.activity"].create(
            {
                "res_model_id": self.model_id,
                "res_id": self.record.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "user_id": self.env.uid,
                "date_deadline": deadline,
            }
        )
        if done:
            activity.action_archive()
        return activity

    def test_gc_is_off_by_default_and_reports_the_contract(self):
        Activity = self.env["mail.activity"]
        old = self._activity(date(2000, 1, 1))
        self.assertEqual(Activity._gc_remove_old_overdue_activities(), (0, False))
        self.assertEqual(Activity._gc_remove_old_done_activities(), (0, False))
        self.assertTrue(old.exists())

    def test_gc_overdue_reports_removed_and_more(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail.activity.gc.delete_overdue_years", "5"
        )
        old = self._activity(date(2000, 1, 1))
        recent = self._activity(date.today())
        removed, more = self.env["mail.activity"]._gc_remove_old_overdue_activities()
        self.assertEqual((removed, more), (1, False))
        self.assertFalse(old.exists())
        self.assertTrue(recent.exists())

    def test_gc_done_activities_are_collected_too(self):
        """Completed activities are archived, so the overdue routine -- which
        searches with the default ``active_test`` -- never saw them and nothing
        aged them out."""
        Activity = self.env["mail.activity"]
        with freeze_time("2000-01-01"):
            done = self._activity(date(2000, 1, 1), done=True)
            self.env.flush_all()
        self.assertFalse(done.active)
        self.assertEqual(done.date_done, date(2000, 1, 1))

        self.env["ir.config_parameter"].sudo().set_param(
            "mail.activity.gc.delete_overdue_years", "5"
        )
        Activity._gc_remove_old_overdue_activities()
        self.assertTrue(done.exists(), "the overdue routine does not see archived rows")

        self.env["ir.config_parameter"].sudo().set_param(
            "mail.activity.gc.delete_done_years", "5"
        )
        removed, more = Activity._gc_remove_old_done_activities()
        self.assertEqual((removed, more), (1, False))
        self.assertFalse(done.exists())

    def test_gc_refuses_a_negative_retention(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "mail.activity.gc.delete_overdue_years", "-1"
        )
        old = self._activity(date(2000, 1, 1))
        with self.assertLogs("odoo.addons.mail.models.mail_activity", "WARNING"):
            self.assertEqual(
                self.env["mail.activity"]._gc_remove_old_overdue_activities(),
                (0, False),
            )
        self.assertTrue(old.exists())


@tests.tagged("mail_activity")
class TestActivityStrandedModel(ActivityScheduleCase):
    """An activity whose ``res_model`` names a model the registry does not have.

    ``res_model_id`` is a plain m2o to ``ir.model``, and an addon installed in
    the database but absent from ``addons_path`` leaves exactly that: the
    ``ir.model`` row and the stored ``res_model`` string survive, the model does
    not. Reproduced end to end by installing ``knowledge`` and re-booting
    without ``enterprise/`` on the path; ``UPDATE`` is the cheap stand-in.

    Every reader must carry such an activity like a document-less one. Before,
    each site below raised a bare ``KeyError`` -- and ``_search`` is on the read
    path of every user who is not the assignee, so one row took the whole list
    down.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.other_user = mail_new_test_user(
            cls.env, login="stranded_reader", groups="base.group_user"
        )
        cls.activity = cls.env["mail.activity"].create(
            {
                "activity_type_id": cls.env.ref("mail.mail_activity_data_todo").id,
                "res_id": cls.record.id,
                "res_model_id": cls.env.ref("test_mail.model_mail_test_activity").id,
                "user_id": cls.user_employee.id,
                "summary": "Act",
            }
        )

    def _strand(self):
        """Point the activity at a model no registry entry answers for."""
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE mail_activity SET res_model = %s WHERE id = %s",
            ("gone.module.model", self.activity.id),
        )
        self.env.invalidate_all()
        self.assertNotIn("gone.module.model", self.env)

    def test_search_survives_for_a_reader_who_is_not_the_assignee(self):
        self._strand()
        Activity = self.env["mail.activity"].with_user(self.other_user)
        self.assertNotIn(self.activity.id, Activity.search([]).ids)
        self.assertFalse(Activity.browse(self.activity.id).has_access("read"))
        Activity.search_count([])

    def test_the_assignee_still_sees_it(self):
        """It stays theirs: only the document half is unreachable."""
        self._strand()
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        self.assertIn(self.activity.id, Activity.search([]).ids)
        self.assertTrue(Activity.browse(self.activity.id).has_access("read"))

    def test_the_systray_still_loads_for_the_assignee(self):
        self._strand()
        groups = (
            self.env["res.users"].with_user(self.user_employee)._get_activity_groups()
        )
        models = {group["model"] for group in groups}
        self.assertIn(
            "mail.activity",
            models,
            'a stranded activity falls into the "Other activities" bucket',
        )

    def test_action_view_document_falls_back(self):
        self._strand()
        action = (
            self.env["mail.activity"]
            .with_user(self.user_employee)
            .browse(self.activity.id)
            .action_view_document()
        )
        self.assertEqual(action["res_model"], "mail.activity")
        self.assertEqual(action["res_id"], self.activity.id)

    def test_the_chatter_side_effects_skip_it(self):
        self._strand()
        activity = self.env["mail.activity"].browse(self.activity.id)
        self.assertFalse(activity._filtered_document_backed())
        self.assertFalse(activity._thread_backed())
        self.assertFalse(activity._filtered_postable())
        activity.action_notify()
        self.assertFalse(activity.action_feedback())

    def test_it_can_still_be_written_and_unlinked(self):
        self._strand()
        activity = (
            self.env["mail.activity"]
            .with_user(self.user_employee)
            .browse(self.activity.id)
        )
        activity.write({"summary": "Renamed"})
        activity.unlink()
        self.assertFalse(activity.exists())


@tests.tagged("mail_activity")
class TestActivityOnAnActivity(TestActivityCommon):
    """``_todo_key`` spells two shapes the same way, and the decode must too.

    A document-less activity is keyed ``('mail.activity', its own id)``; an
    activity filed *against* a ``mail.activity`` record is keyed
    ``('mail.activity', that record's id)``. Both name the same record and both
    must count once -- which is what ``_get_activity_groups`` does. But
    ``_todo_keys_elsewhere`` used to decode the key only as the document-less
    shape, so it never saw the other activity holding it, and the badge was
    decremented twice for one record going quiet.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.activity_model_id = cls.env["ir.model"]._get_id("mail.activity")

    def _systray_counter(self):
        groups = (
            self.env["res.users"].with_user(self.user_employee)._get_activity_groups()
        )
        return sum(group.get("due_count", 0) for group in groups)

    def _due_activity(self, **vals):
        return self.env["mail.activity"].create(
            {
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "date_deadline": fields.Date.context_today(
                    self.env["mail.activity"].with_user(self.user_employee)
                ),
                "user_id": self.user_employee.id,
                **vals,
            }
        )

    def _bus_total(self, func):
        """Sum of the count_diff the bus carried while `func` ran."""
        seen = []
        origin = type(self.env["res.users"])._bus_send

        def spy(records, notification_type, message, /, **kwargs):
            if notification_type == "mail.activity/updated":
                seen.append(message.get("count_diff", 0))
            return origin(records, notification_type, message, **kwargs)

        with patch.object(type(self.env["res.users"]), "_bus_send", spy):
            func()
            self.env.flush_all()
        return sum(seen)

    def test_the_bus_delta_tracks_the_badge_through_a_nested_activity(self):
        free = self._due_activity(summary="Free")
        self.env.flush_all()
        nested = self._due_activity(
            summary="On the free one",
            res_model_id=self.activity_model_id,
            res_id=free.id,
        )
        self.env.flush_all()

        before = self._systray_counter()
        delta = self._bus_total(free.unlink)
        after = self._systray_counter()
        self.assertEqual(
            delta,
            after - before,
            "the bus must move the badge by exactly what a reload would show",
        )
        self.assertFalse(
            nested.exists(), "deleting the record cascades to activities filed on it"
        )

    def test_two_activities_on_one_record_count_once(self):
        free = self._due_activity(summary="Free")
        self.env.flush_all()
        before = self._systray_counter()
        delta = self._bus_total(
            lambda: self._due_activity(
                summary="On the free one",
                res_model_id=self.activity_model_id,
                res_id=free.id,
            )
        )
        self.assertEqual(
            self._systray_counter(), before, "both activities make the same record busy"
        )
        self.assertEqual(delta, 0)


@tests.tagged("mail_activity")
class TestActivityNotifyCost(TestActivityCommon):
    """``action_notify`` must not work for activities it will not notify.

    Every query-count pin in this file exercises a single activity, so a per
    record cost in a batch path is invisible to all of them; these assert the
    shape at N > 1.
    """

    def _schedule(self, count, user):
        """Create `count` activities without notifying.

        `create` notifies an assignee that is not the actor, which is the thing
        under test here -- so the fixture stays quiet and each test triggers the
        one round it means to measure.
        """
        records = self.env["mail.test.activity"].create(
            [{"name": f"Doc {index}"} for index in range(count)]
        )
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "res_id": record.id,
                        "res_model_id": self.env["ir.model"]._get_id(
                            "mail.test.activity"
                        ),
                        "user_id": user.id if user else False,
                        "summary": "Act",
                    }
                    for record in records
                ]
            )
        )

    def test_unassigned_activities_render_nothing(self):
        activities = self._schedule(5, user=None)
        self.env.invalidate_all()
        with patch.object(
            type(self.env["ir.qweb"]),
            "_render",
            side_effect=AssertionError("rendered a notification with no assignee"),
        ):
            activities.action_notify()

    def test_notifying_does_not_re_derive_the_document_per_activity(self):
        """The reply-to follows the document, so it is resolved for the batch
        rather than once per activity.

        The guarantee is "not per record", not "exactly one call": a future
        cache could reach zero, and reading an exact count as a verdict is what
        cost two sessions an afternoon here (`coding_guidelines.rst` §6.4). So
        bound the derivations, then assert the mechanism actually delivered.
        """
        activities = self._schedule(5, user=self.user_employee)
        self.env.invalidate_all()
        with patch.object(
            type(self.env["mail.test.activity"]),
            "_notify_get_reply_to",
            autospec=True,
            side_effect=lambda records, **kwargs: dict.fromkeys(
                records.ids, "reply@test.lan"
            ),
        ) as reply_to:
            activities.action_notify()

        self.assertLessEqual(
            reply_to.call_count, 1, "derived for the batch, never once per activity"
        )
        if reply_to.call_count:
            self.assertEqual(
                len(reply_to.call_args[0][0]),
                5,
                "the one derivation covers all five documents",
            )
        messages = self.env["mail.message"].search(
            [
                ("model", "=", "mail.test.activity"),
                ("res_id", "in", activities.mapped("res_id")),
                ("message_type", "=", "user_notification"),
            ]
        )
        self.assertEqual(len(messages), 5)
        self.assertEqual(
            set(messages.mapped("reply_to")),
            {"reply@test.lan"},
            "every notification still carries the resolved reply-to",
        )

    def test_the_model_description_is_in_the_assignees_language(self):
        """The assignee reads the notification, so the model's translated name
        must resolve in *their* language, not in the actor's.

        Hoisting `model_description` out of the per-assignee language context is
        the easy way to lose this, and it costs nothing visible until somebody
        runs a database with two languages.
        """
        self.env["res.lang"]._activate_lang("fr_FR")
        model = self.env["ir.model"]._get("mail.test.activity")
        model.with_context(lang="fr_FR").name = "Modele De Test"
        self.env.flush_all()
        french_user = mail_new_test_user(
            self.env, login="activity_fr", groups="base.group_user", lang="fr_FR"
        )
        record = self.env["mail.test.activity"].create({"name": "Doc"})
        activity = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "res_id": record.id,
                    "res_model_id": self.env["ir.model"]._get_id("mail.test.activity"),
                    "summary": "Act",
                    "user_id": french_user.id,
                }
            )
        )
        activity.action_notify()
        message = self.env["mail.message"].search(
            [
                ("model", "=", "mail.test.activity"),
                ("res_id", "=", record.id),
                ("message_type", "=", "user_notification"),
            ],
            limit=1,
            order="id desc",
        )
        self.assertIn("Modele De Test", str(message.body))

    def test_two_activities_on_one_record_each_get_their_notification(self):
        """`_message_notify_batch` keys bodies by record, so two activities on
        one record cannot share a batch entry -- they must go in successive
        rounds rather than one overwriting the other."""
        record = self.env["mail.test.activity"].create({"name": "Doc"})
        common = {
            "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
            "date_deadline": fields.Date.context_today(self.env["mail.activity"]),
            "res_id": record.id,
            "res_model_id": self.env["ir.model"]._get_id("mail.test.activity"),
            "user_id": self.user_employee.id,
        }
        activities = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create([{**common, "summary": "First"}, {**common, "summary": "Second"}])
        )
        activities.action_notify()
        messages = self.env["mail.message"].search(
            [
                ("model", "=", "mail.test.activity"),
                ("res_id", "=", record.id),
                ("message_type", "=", "user_notification"),
            ]
        )
        self.assertEqual(len(messages), 2, "one notification per activity")
        bodies = " ".join(str(message.body) for message in messages)
        self.assertIn("First", bodies)
        self.assertIn("Second", bodies)

    def test_one_batch_keeps_each_document_its_own_company(self):
        """A batch spans documents; the company, alias domain and reply-to do not.

        This works only because `action_notify` does NOT pre-resolve them:
        `_message_notify_batch` derives them itself, per record. Passing them as
        kwargs would write one value across the whole batch.
        """
        second_company = self.env["res.company"].create({"name": "Second Co"})
        domains = self.env["mail.alias.domain"].create(
            [
                {"name": "one.test", "bounce_alias": "b1", "catchall_alias": "c1"},
                {"name": "two.test", "bounce_alias": "b2", "catchall_alias": "c2"},
            ]
        )
        self.env.company.alias_domain_id = domains[0]
        second_company.alias_domain_id = domains[1]
        records = self.env["res.partner"].create(
            [
                {"name": "in co1", "company_id": self.env.company.id},
                {"name": "in co2", "company_id": second_company.id},
            ]
        )
        # same assignee, type and deadline: exactly one batch
        self.env["mail.activity"].with_context(mail_activity_quick_update=True).create(
            [
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "date_deadline": date(2026, 9, 1),
                    "res_id": record.id,
                    "res_model_id": self.env["ir.model"]._get_id("res.partner"),
                    "summary": "Act",
                    "user_id": self.user_employee.id,
                }
                for record in records
            ]
        ).action_notify()
        messages = self.env["mail.message"].search(
            [
                ("model", "=", "res.partner"),
                ("res_id", "in", records.ids),
                ("message_type", "=", "user_notification"),
            ],
            order="res_id",
        )
        self.assertEqual(len(messages), 2)
        self.assertEqual(
            messages.mapped("record_company_id"), self.env.company + second_company
        )
        self.assertEqual(messages.mapped("record_alias_domain_id"), domains)

    def test_two_types_sharing_a_name_are_not_merged(self):
        """The grouping key carries the activity type as a record, not as its name.

        The name is translated, so keying on it would merge two types that
        collide in the actor's language and hand one of them the other's
        subtitle in the assignee's.
        """
        self.env["res.lang"]._activate_lang("fr_FR")
        types = self.env["mail.activity.type"].create(
            [{"name": "Same Name"}, {"name": "Same Name"}]
        )
        types[0].with_context(lang="fr_FR").name = "Premier"
        types[1].with_context(lang="fr_FR").name = "Second"
        french_user = mail_new_test_user(
            self.env, login="activity_fr_types", groups="base.group_user", lang="fr_FR"
        )
        records = self.env["mail.test.activity"].create([{"name": "A"}, {"name": "B"}])
        activities = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "activity_type_id": activity_type.id,
                        "date_deadline": date(2026, 9, 1),
                        "res_id": record.id,
                        "res_model_id": self.env["ir.model"]._get_id(
                            "mail.test.activity"
                        ),
                        "user_id": french_user.id,
                    }
                    for activity_type, record in zip(types, records, strict=True)
                ]
            )
        )
        seen = []
        Thread = type(self.env["mail.test.activity"])
        origin = Thread._message_notify_batch

        def spy(records, bodies, **kwargs):
            seen.append(kwargs.get("subtitles"))
            return origin(records, bodies, **kwargs)

        with patch.object(Thread, "_message_notify_batch", spy):
            activities.action_notify()
        self.assertEqual(len(seen), 2, "two types, two batches")
        # The label is the assignee's too, not only the type name it wraps.
        self.assertIn("Activité : Premier", seen[0] + seen[1])
        self.assertIn("Activité : Second", seen[0] + seen[1])


@tests.tagged("mail_activity")
class TestActivityUnlinkBookkeeping(ActivityScheduleCase):
    """Unlinking activities that owe nothing must not go looking for keys."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")

    def _activity(self, **vals):
        return self.env["mail.activity"].create(
            {
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                "res_id": self.record.id,
                "res_model_id": self.model_id,
                "user_id": self.env.uid,
                **vals,
            }
        )

    def test_unlinking_archived_activities_says_nothing(self):
        activities = self._activity() + self._activity()
        activities.action_archive()
        self.env.flush_all()
        self._reset_bus()
        activities.with_context(active_test=False).unlink()
        self.assertBusNotifications([], [])

    def test_unlinking_a_due_activity_still_says_so(self):
        activity = self._activity(date_deadline=date(2000, 1, 1))
        self.env.flush_all()
        self._reset_bus()
        with self.assertBus(
            [(self.env.cr.dbname, "res.partner", self.env.user.partner_id.id)],
            [
                {
                    "type": "mail.activity/updated",
                    "payload": {"activity_deleted": True, "count_diff": -1},
                }
            ],
        ):
            activity.unlink()


@tests.tagged("mail_activity")
class TestActivityDeadlineClock(ActivityScheduleCase):
    """A deadline names a day in the *assignee's* timezone, everywhere.

    ``action_reschedule_today`` has always resolved "today" that way -- it
    groups by ``user_tz``. Creation did not: it used ``context_today``, the
    actor's day. The two disagreed whenever the pair sat either side of a date
    line, so an activity scheduled for "today" was born ``overdue`` and pressing
    the very same word on it moved it a day and turned it green.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mexico = mail_new_test_user(
            cls.env,
            login="act_mexico",
            groups="base.group_user",
            tz="America/Mexico_City",
        )
        cls.madrid = mail_new_test_user(
            cls.env, login="act_madrid", groups="base.group_user", tz="Europe/Madrid"
        )
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.todo = cls.env.ref("mail.mail_activity_data_todo")

    def _mexico_env(self):
        """The actor's env, with the session context a login would build."""
        return self.env(
            user=self.mexico,
            context=self.env["res.users"].with_user(self.mexico).context_get(),
        )

    # 01:00 UTC on the 17th is 19:00 on the 16th in Mexico City and 03:00 on
    # the 17th in Madrid: the two are on different days.
    FROZEN = "2026-08-17 01:00:00"

    @freeze_time(FROZEN)
    def test_todo_domain_counts_from_the_assignee_day(self):
        """_domain_todo is the domain form of "already due for you",
        the predicate _filtered_todo applies in Python. It has to read the same
        clock: at 01:00 UTC Madrid is a day ahead of Mexico City, so an activity
        due on Madrid's today is not yet due on Mexico's."""
        Activity = self.env["mail.activity"]
        for user in (self.mexico, self.madrid):
            Activity.create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": user.id,
                    "date_deadline": Activity._today_in_tz(user.tz),
                }
            )
        self.env.flush_all()
        self.env.invalidate_all()

        for user in (self.mexico, self.madrid):
            with self.subTest(user=user.login):
                due = Activity.search(Activity._domain_todo(user))
                self.assertEqual(
                    due.user_id,
                    user,
                    "the domain must select that user's activities only",
                )
                self.assertEqual(
                    due,
                    due._filtered_todo(),
                    "the domain and the Python predicate must agree",
                )
                self.assertEqual(set(due.mapped("state")), {"today"})

        # and the two users are genuinely on different days here
        self.assertNotEqual(
            Activity._today_in_tz(self.mexico.tz),
            Activity._today_in_tz(self.madrid.tz),
        )

    @freeze_time(FROZEN)
    def test_create_counts_from_the_assignee_day(self):
        activity = (
            self._mexico_env()["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.madrid.id,
                }
            )
        )
        self.env.invalidate_all()
        self.assertEqual(
            activity.date_deadline,
            date(2026, 8, 17),
            "the assignee's today, not the scheduler's",
        )
        self.assertEqual(
            activity.state,
            "today",
            "an activity scheduled for today is never born overdue",
        )

    @freeze_time(FROZEN)
    def test_create_and_reschedule_today_agree(self):
        """The regression this class exists for: same word, same day."""
        activity = (
            self._mexico_env()["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.madrid.id,
                }
            )
        )
        self.env.invalidate_all()
        created = activity.date_deadline
        activity.action_reschedule_today()
        self.env.invalidate_all()
        self.assertEqual(
            created,
            activity.date_deadline,
            "create and 'Today' must resolve the same day",
        )

    @freeze_time(FROZEN)
    def test_activity_schedule_counts_from_the_assignee_day(self):
        """The automation path -- every addon that schedules for someone else."""
        activity = (
            self.record.with_user(self.mexico)
            .with_context(
                self.env["res.users"].with_user(self.mexico).context_get(),
                mail_activity_quick_update=True,
            )
            .activity_schedule("mail.mail_activity_data_todo", user_id=self.madrid.id)
        )
        self.env.invalidate_all()
        self.assertEqual(activity.date_deadline, date(2026, 8, 17))
        self.assertEqual(activity.state, "today")

    @freeze_time(FROZEN)
    def test_explicit_deadline_is_never_rebased(self):
        """Only an *implicit* deadline is the assignee's day; a given one stands."""
        activity = (
            self._mexico_env()["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "date_deadline": date(2026, 8, 16),
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.madrid.id,
                }
            )
        )
        self.assertEqual(activity.date_deadline, date(2026, 8, 16))

    @freeze_time(FROZEN)
    def test_an_unassigned_activity_is_not_born_overdue(self):
        """No assignee means no ``user_tz``, so both ends resolve to UTC.

        The fallback is deliberately not the caller's timezone -- that would make
        one activity show a different state to each reader. It is safe only
        because the deadline default is counted from the same helper, so the two
        ends of the comparison keep one clock.
        """
        actor = self._mexico_env()
        activity = (
            actor["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                }
            )
        )
        self.env.invalidate_all()
        self.assertFalse(activity.user_tz)
        self.assertEqual(activity.state, "today")

    @freeze_time(FROZEN)
    def test_an_unassigned_activity_reads_the_same_to_everyone(self):
        """Reader-independence is the reason the fallback is UTC."""
        activity = (
            self._mexico_env()["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                }
            )
        )
        self.env.invalidate_all()
        states = {
            tz: activity.with_context(tz=tz).state
            for tz in ("UTC", "Pacific/Kiritimati", "Pacific/Pago_Pago")
        }
        self.assertEqual(set(states.values()), {"today"}, states)

    @freeze_time(FROZEN)
    def test_sql_state_agrees_with_the_computed_one(self):
        """``_sql_today``'s ELSE branch must spell the same fallback.

        The grouped and searched states come from SQL and the displayed one from
        Python; if their fallbacks differ, an unassigned activity is filed in one
        bucket and drawn in another.
        """
        actor = self._mexico_env()
        actor["mail.activity"].with_context(mail_activity_quick_update=True).create(
            {
                "activity_type_id": self.todo.id,
                "res_id": self.record.id,
                "res_model_id": self.model_id,
            }
        )
        self.env.flush_all()
        Doc = actor["mail.test.activity"]
        self.assertIn(
            self.record,
            Doc.search([("activity_state", "=", "today")]),
            "the SQL path must see the same day the compute does",
        )
        groups = dict(
            Doc._read_group(
                [("id", "=", self.record.id)], ["activity_state"], ["__count"]
            )
        )
        self.assertEqual(list(groups), ["today"])


@tests.tagged("mail_activity")
class TestActivityNotificationLanguage(ActivityScheduleCase):
    """The whole notification is the assignee's, label included.

    ``action_notify`` builds ``localized`` for the assignee and used it for the
    body and the date format, then called the bare ``_()`` for the subject and
    the subtitles. That helper reads the language off the calling frame's
    ``self``, which is the *actor's* recordset -- so a French assignee got a
    Spanish label wrapped around a French value.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.env["res.lang"]._activate_lang("es_ES")
        cls.spanish_actor = mail_new_test_user(
            cls.env, login="act_es", groups="base.group_user", lang="es_ES"
        )
        cls.french_assignee = mail_new_test_user(
            cls.env, login="act_fr", groups="base.group_user", lang="fr_FR"
        )
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})

    def test_subtitles_and_subject_are_in_the_assignee_language(self):
        activity = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "date_deadline": date(2026, 9, 1),
                    "res_id": self.record.id,
                    "res_model_id": self.env["ir.model"]._get_id("mail.test.activity"),
                    "summary": "Act",
                    "user_id": self.french_assignee.id,
                }
            )
        )
        seen = []
        Thread = type(self.env["mail.test.activity"])
        origin = Thread._message_notify_batch

        def spy(records, bodies, **kwargs):
            seen.append(
                (kwargs.get("subtitles"), list(kwargs.get("subjects").values()))
            )
            return origin(records, bodies, **kwargs)

        actor_env = self.env(
            user=self.spanish_actor,
            context=self.env["res.users"].with_user(self.spanish_actor).context_get(),
        )
        with patch.object(Thread, "_message_notify_batch", spy):
            activity.with_env(actor_env).action_notify()

        self.assertEqual(len(seen), 1)
        subtitles, subjects = seen[0]
        self.assertTrue(
            any(subtitle.startswith("Activité") for subtitle in subtitles),
            f"the label must be French, got {subtitles}",
        )
        self.assertTrue(
            any(subtitle.startswith("Date limite") for subtitle in subtitles),
            f"the deadline label must be French, got {subtitles}",
        )
        self.assertTrue(
            all("Actividad" not in subtitle for subtitle in subtitles),
            "nothing may come out in the actor's language",
        )
        self.assertTrue(
            all("assigned to you" not in subject for subject in subjects),
            f"the subject must be French too, got {subjects}",
        )


@tests.tagged("mail_activity")
class TestActivityResNameFollowsRenames(ActivityScheduleCase):
    """``res_name`` is stored and no ``depends`` can reach the document's name.

    ``res_id`` is a ``Many2oneReference``, so the document has to push the
    recompute. Without it the activity list keeps the old name forever and the
    view's own ``res_name ilike`` filter matches a name nothing has.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Original"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")

    def _activity(self, **vals):
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.env.uid,
                    **vals,
                }
            )
        )

    def test_renaming_the_document_refreshes_res_name(self):
        activity = self._activity(summary="A")
        self.env.flush_all()
        self.assertEqual(activity.res_name, "Original")
        self.record.name = "Renamed"
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(activity.res_name, "Renamed")

    def test_the_stored_column_is_refreshed_not_just_the_cache(self):
        activity = self._activity(summary="A")
        self.env.flush_all()
        self.record.name = "Renamed"
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT res_name FROM mail_activity WHERE id = %s", (activity.id,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], "Renamed")

    def test_the_search_filter_follows_the_rename(self):
        """`mail_activity_views.xml` filters on `res_name ilike`."""
        activity = self._activity(summary="A")
        self.env.flush_all()
        self.record.name = "Renamed"
        self.env.flush_all()
        Activity = self.env["mail.activity"]
        self.assertFalse(
            Activity.search(
                [("id", "=", activity.id), ("res_name", "ilike", "Original")]
            ),
            "the old name must stop matching",
        )
        self.assertEqual(
            Activity.search(
                [("id", "=", activity.id), ("res_name", "ilike", "Renamed")]
            ),
            activity,
        )

    def test_completed_activities_are_refreshed_too(self):
        """A done activity still shows its document, so it still needs the name."""
        activity = self._activity(summary="A")
        activity.action_feedback(feedback="done")
        self.env.flush_all()
        self.assertFalse(activity.active)
        self.record.name = "Renamed"
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(activity.res_name, "Renamed")

    def test_two_activities_on_one_record_never_disagree(self):
        first = self._activity(summary="A")
        self.env.flush_all()
        self.record.name = "Renamed"
        self.env.flush_all()
        second = self._activity(summary="B")
        self.env.invalidate_all()
        self.assertEqual(first.res_name, second.res_name)

    def test_an_unrelated_write_costs_no_recompute(self):
        """Only a rename pushes; writing anything else must not."""
        self._activity(summary="A")
        self.env.flush_all()
        self.env.invalidate_all()
        with patch.object(
            type(self.env["mail.activity"]),
            "_compute_res_name",
            side_effect=AssertionError("recomputed on an unrelated write"),
        ):
            self.record.write({"email_from": "x@test.lan"})
            self.env.flush_all()


@tests.tagged("mail_activity")
class TestActivityIntegrityGuards(ActivityScheduleCase):
    """Guards over the two shapes that used to corrupt data silently."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.todo = cls.env.ref("mail.mail_activity_data_todo")

    def _activity(self, **vals):
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.env.uid,
                    **vals,
                }
            )
        )

    def test_writing_res_model_is_refused(self):
        """`res_model` is a *stored* related field: `readonly` does not stop a
        programmatic write, and the value lands in the column without touching
        `res_model_id` -- permanently, since nothing recomputes it."""
        activity = self._activity(summary="A")
        self.env.flush_all()
        with self.assertRaises(exceptions.UserError):
            activity.write({"res_model": "mail.test.simple"})
        self.env.invalidate_all()
        self.assertEqual(activity.res_model, activity.res_model_id.model)

    def test_creating_with_res_model_still_works(self):
        """`create` is safe -- the related precompute wins -- and must stay so:
        callers and `_prepare_next_activity_values` overrides pass it."""
        activity = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "res_model": "mail.test.activity",
                    "user_id": self.env.uid,
                }
            )
        )
        self.env.flush_all()
        self.assertEqual(activity.res_model, "mail.test.activity")
        self.assertEqual(activity.res_model_id.id, self.model_id)

    def test_prepare_next_activity_values_does_not_name_res_model(self):
        """Naming both invites them to disagree; `res_model_id` is the source."""
        activity = self._activity(summary="A")
        vals = activity._prepare_next_activity_values()
        self.assertNotIn("res_model", vals)
        self.assertEqual(vals["res_model_id"], self.model_id)

    def test_feedback_attachments_are_not_shared_between_messages(self):
        """`message_post` re-parents attachments onto the document, so one
        record shared by several messages is owned by exactly one of them --
        and deleting that one document takes the file out of all the others."""
        records = self.env["mail.test.activity"].create(
            [{"name": f"D{index}"} for index in range(3)]
        )
        activities = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "activity_type_id": self.todo.id,
                        "res_id": record.id,
                        "res_model_id": self.model_id,
                        "user_id": self.env.uid,
                    }
                    for record in records
                ]
            )
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "proof.txt",
                "datas": b"aGk=",
                "res_model": "mail.compose.message",
                "res_id": 0,
            }
        )
        self.env.flush_all()

        messages, __ = activities._action_done(
            feedback="done", attachment_ids=attachment.ids
        )
        self.env.flush_all()
        self.assertEqual(len(messages), 3)
        attachment_ids = [message.attachment_ids for message in messages]
        self.assertTrue(
            all(len(ids) == 1 for ids in attachment_ids),
            "every message keeps its evidence",
        )
        self.assertEqual(
            len({ids.id for ids in attachment_ids}),
            3,
            "three messages, three attachment records -- not one shared three ways",
        )

        # the original owner going away must not empty the other two
        records[0].unlink()
        self.env.flush_all()
        self.env.invalidate_all()
        survivors = messages[1:].exists()
        self.assertEqual(len(survivors), 2)
        for message in survivors:
            self.assertTrue(
                message.attachment_ids.exists(),
                "deleting one document must not strip another record's chatter",
            )

    def test_get_activity_data_is_bounded(self):
        """It is RPC-reachable; without a cap it materialises the whole table."""
        Activity = self.env["mail.activity"]
        records = self.env["mail.test.activity"].create(
            [{"name": f"B{index}"} for index in range(5)]
        )
        Activity.with_context(mail_activity_quick_update=True).create(
            [
                {
                    "activity_type_id": self.todo.id,
                    "res_id": record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.env.uid,
                }
                for record in records
            ]
        )
        self.env.flush_all()

        seen = []
        origin = type(self.env["mail.test.activity"])._search

        def spy(records, domain, offset=0, limit=None, order=None, **kwargs):
            seen.append(limit)
            return origin(records, domain, offset, limit, order, **kwargs)

        with patch.object(type(self.env["mail.test.activity"]), "_search", spy):
            Activity.get_activity_data("mail.test.activity", [])
        self.assertTrue(seen, "the documents are selected through their own model")
        self.assertEqual(
            seen[0],
            Activity._VIEW_DATA_MAX_LIMIT,
            "a call with no limit is capped, not left unbounded",
        )

        seen.clear()
        with patch.object(type(self.env["mail.test.activity"]), "_search", spy):
            Activity.get_activity_data("mail.test.activity", [], limit=2)
        self.assertEqual(seen[0], 2, "a caller-supplied limit is honoured")

        seen.clear()
        with patch.object(type(self.env["mail.test.activity"]), "_search", spy):
            Activity.get_activity_data("mail.test.activity", [], limit=10**6)
        self.assertEqual(
            seen[0], Activity._VIEW_DATA_MAX_LIMIT, "and an absurd one is clamped"
        )


@tests.tagged("mail_activity")
class TestActivityDocumentModelIntegrity(ActivityScheduleCase):
    """`res_model` is a stored related on `res_model_id.model`.

    `readonly` does not stop a programmatic write and the field is stored, so a
    write landed in the column without ever touching `res_model_id` -- and
    nothing recomputed it afterwards. Every reader (`_filtered_document_backed`,
    `_thread_backed`, `_check_access`, `_search`) then worked off a model the
    activity is not actually filed on.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")

    def _activity(self):
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.env.uid,
                }
            )
        )

    def test_writing_res_model_is_refused(self):
        activity = self._activity()
        with self.assertRaises(exceptions.UserError):
            activity.write({"res_model": "mail.test.simple"})

    def test_the_pair_cannot_be_desynchronised(self):
        activity = self._activity()
        with self.assertRaises(exceptions.UserError):
            activity.write({"res_model": "mail.test.simple"})
        self.env.invalidate_all()
        self.assertEqual(activity.res_model, activity.res_model_id.model)

    def test_creating_with_a_contradicting_res_model_keeps_them_in_step(self):
        """`create` was already safe -- the related precompute wins. Pin it."""
        activity = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "res_model": "mail.test.simple",
                    "user_id": self.env.uid,
                }
            )
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(activity.res_model, "mail.test.activity")
        self.assertEqual(activity.res_model, activity.res_model_id.model)

    def test_the_chained_values_do_not_carry_res_model(self):
        """`_prepare_next_activity_values` feeds `create`; naming both invites
        exactly the desynchronisation above."""
        activity = self._activity()
        vals = activity._prepare_next_activity_values()
        self.assertNotIn("res_model", vals)
        self.assertEqual(vals["res_model_id"], self.model_id)


@tests.tagged("mail_activity")
class TestActivityFeedbackAttachments(ActivityScheduleCase):
    """A completion message must own the attachments it shows.

    `message_post` re-parents the attachments it is handed onto the document, so
    one attachment record handed to several messages ends up owned by exactly
    one of them -- and deleting that one document took the file out of all the
    others' chatter.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.records = cls.env["mail.test.activity"].create(
            [{"name": f"Doc {index}"} for index in range(3)]
        )

    def _activities(self):
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "res_id": record.id,
                        "res_model_id": self.model_id,
                        "user_id": self.env.uid,
                    }
                    for record in self.records
                ]
            )
        )

    def _attachment(self):
        return self.env["ir.attachment"].create(
            {
                "name": "shared.txt",
                "datas": b"aGk=",
                "res_model": "mail.compose.message",
                "res_id": 0,
            }
        )

    def test_each_message_gets_its_own_attachment(self):
        activities = self._activities()
        attachment = self._attachment()
        messages, __ = activities._action_done(
            feedback="done", attachment_ids=attachment.ids
        )
        self.env.flush_all()
        self.assertEqual(len(messages), 3)
        attachment_ids = [message.attachment_ids for message in messages]
        self.assertTrue(all(len(ids) == 1 for ids in attachment_ids))
        self.assertEqual(
            len({ids.id for ids in attachment_ids}),
            3,
            "three messages, three attachment records",
        )

    def test_deleting_one_document_leaves_the_others_intact(self):
        """The data loss this class exists for."""
        activities = self._activities()
        attachment = self._attachment()
        messages, __ = activities._action_done(
            feedback="done", attachment_ids=attachment.ids
        )
        self.env.flush_all()
        survivors = messages[1:]
        surviving_attachment_ids = survivors.attachment_ids.ids
        self.records[0].unlink()
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(
            self.env["ir.attachment"].browse(surviving_attachment_ids).exists().ids,
            surviving_attachment_ids,
            "deleting one document must not strip the others of their files",
        )
        for message in survivors:
            self.assertTrue(message.attachment_ids)

    def test_a_single_activity_still_uses_the_attachment_as_given(self):
        """No copy when there is nothing to share it with."""
        activity = self._activities()[0]
        attachment = self._attachment()
        messages, __ = activity._action_done(
            feedback="done", attachment_ids=attachment.ids
        )
        self.assertEqual(messages.attachment_ids, attachment)


@tests.tagged("mail_activity")
class TestActivityViewDataLimit(ActivityScheduleCase):
    """`get_activity_data` is RPC-reachable; an absent limit is not "no limit"."""

    def test_limit_is_capped_even_when_none_is_asked_for(self):
        Activity = self.env["mail.activity"]
        captured = {}
        origin = type(Activity)._get_activity_data_activities

        def spy(model, res_model, domain, limit, offset, fetch_done):
            captured["limit"] = limit
            return origin(model, res_model, domain, limit, offset, fetch_done)

        with patch.object(type(Activity), "_get_activity_data_activities", spy):
            Activity.get_activity_data("mail.test.activity", [])
        self.assertEqual(captured["limit"], Activity._VIEW_DATA_MAX_LIMIT)

    def test_an_oversized_limit_is_clamped(self):
        Activity = self.env["mail.activity"]
        captured = {}
        origin = type(Activity)._get_activity_data_activities

        def spy(model, res_model, domain, limit, offset, fetch_done):
            captured["limit"] = limit
            return origin(model, res_model, domain, limit, offset, fetch_done)

        with patch.object(type(Activity), "_get_activity_data_activities", spy):
            Activity.get_activity_data("mail.test.activity", [], limit=10**9)
        self.assertEqual(captured["limit"], Activity._VIEW_DATA_MAX_LIMIT)

    def test_a_reasonable_limit_is_honoured(self):
        Activity = self.env["mail.activity"]
        captured = {}
        origin = type(Activity)._get_activity_data_activities

        def spy(model, res_model, domain, limit, offset, fetch_done):
            captured["limit"] = limit
            return origin(model, res_model, domain, limit, offset, fetch_done)

        with patch.object(type(Activity), "_get_activity_data_activities", spy):
            Activity.get_activity_data("mail.test.activity", [], limit=20)
        self.assertEqual(captured["limit"], 20)


@tests.tagged("mail_activity")
class TestActivityPager(TestActivityCommon):
    """`_search` filters in Python, so the page is not the match set.

    A Query built from an id list answers `count_matching` about its own rows.
    For every Query the ORM builds that is right; for the one `_search` returns
    here the id list *is* the page, so the list view read its page size as the
    total and disabled its own next-page control -- the rows past the first page
    were unreachable.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pager_user = mail_new_test_user(
            cls.env, login="pager_user", groups="base.group_user"
        )
        cls.pager_records = cls.env["mail.test.activity"].create(
            [{"name": f"pager {index:03d}"} for index in range(25)]
        )
        model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        activity_type = cls.env.ref("mail.mail_activity_data_todo")
        cls.pager_activities = (
            cls.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "res_model_id": model_id,
                        "res_id": record.id,
                        "user_id": cls.pager_user.id,
                        "activity_type_id": activity_type.id,
                        "summary": record.name,
                    }
                    for record in cls.pager_records
                ]
            )
        )

    def _own_domain(self):
        return [("id", "in", self.pager_activities.ids)]

    def test_the_pager_counts_the_match_set_not_the_page(self):
        Activity = self.env["mail.activity"].with_user(self.pager_user)
        result = Activity.web_search_read(
            self._own_domain(), {"summary": {}}, limit=5, count_limit=10001
        )
        self.assertEqual(len(result["records"]), 5, "the page is still a page")
        self.assertEqual(
            result["length"],
            25,
            "the pager must be told how many rows match, not how many it got",
        )

    def test_the_count_honours_count_limit(self):
        """The count is a scan; the client's bound is what keeps it affordable."""
        Activity = self.env["mail.activity"].with_user(self.pager_user)
        result = Activity.web_search_read(
            self._own_domain(), {"summary": {}}, limit=5, count_limit=10
        )
        self.assertEqual(result["length"], 10)

    def test_the_page_past_the_first_is_reachable_and_disjoint(self):
        Activity = self.env["mail.activity"].with_user(self.pager_user)
        first = Activity.web_search_read(
            self._own_domain(), {"id": {}}, limit=5, offset=0, order="id ASC"
        )
        second = Activity.web_search_read(
            self._own_domain(), {"id": {}}, limit=5, offset=5, order="id ASC"
        )
        first_ids = [record["id"] for record in first["records"]]
        second_ids = [record["id"] for record in second["records"]]
        self.assertEqual(len(second_ids), 5)
        self.assertFalse(set(first_ids) & set(second_ids))
        self.assertEqual(first["length"], 25)
        self.assertEqual(second["length"], 25)

    def test_search_count_is_unchanged(self):
        Activity = self.env["mail.activity"].with_user(self.pager_user)
        self.assertEqual(Activity.search_count(self._own_domain()), 25)
        self.assertEqual(Activity.search_count(self._own_domain(), limit=7), 7)

    def test_the_count_respects_access(self):
        """Counting must not widen what the scan narrowed."""
        other = mail_new_test_user(
            self.env, login="pager_other", groups="base.group_user"
        )
        Activity = self.env["mail.activity"].with_user(other)
        result = Activity.web_search_read(
            self._own_domain(), {"summary": {}}, limit=5, count_limit=10001
        )
        self.assertEqual(
            result["length"],
            len(Activity.search(self._own_domain())),
            "the count and the search must agree about what `other` may see",
        )


@tests.tagged("mail_activity")
class TestActivityNotifyAccess(TestActivityCommon):
    """`mail_activity_rule_user` grants write to the creator and the assignee.

    security/mail_security.xml says why: so they can manage an activity on a
    document they cannot write. Reassigning one then notified the new assignee
    through an unsudoed `_message_notify_batch`, which derives the document's
    alias domain and company from the recordset -- and raised AccessError for
    exactly the callers the rule exists to admit.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "Notify Co B"})
        cls.owner = mail_new_test_user(
            cls.env,
            login="notify_owner",
            groups="base.group_user",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id, cls.company_b.id])],
        )
        cls.colleague = mail_new_test_user(
            cls.env, login="notify_colleague", groups="base.group_user"
        )
        cls.hidden_record = cls.env["mail.test.multi.company.with.activity"].create(
            {"name": "co-B document", "company_id": cls.company_b.id}
        )
        cls.hidden_activity = (
            cls.env["mail.activity"]
            .with_user(cls.owner)
            .with_context(
                allowed_company_ids=[cls.company_a.id, cls.company_b.id],
                mail_activity_quick_update=True,
            )
            .create(
                {
                    "res_model_id": cls.env["ir.model"]._get_id(
                        "mail.test.multi.company.with.activity"
                    ),
                    "res_id": cls.hidden_record.id,
                    "user_id": cls.owner.id,
                    "activity_type_id": cls.env.ref("mail.mail_activity_data_todo").id,
                    "summary": "in the other company",
                }
            )
        )
        # and then the owner loses that company: an ordinary state, and the one
        # a single-company fixture cannot express at all.
        cls.owner.write(
            {
                "company_ids": [(6, 0, [cls.company_a.id])],
                "company_id": cls.company_a.id,
            }
        )
        # re-browsed off a clean env: the creating context still names company B,
        # which env.companies now refuses for this user.
        cls.hidden_activity = cls.env["mail.activity"].browse(cls.hidden_activity.id)

    def test_the_fixture_really_hides_the_document(self):
        Document = self.env["mail.test.multi.company.with.activity"].with_user(
            self.owner
        )
        self.assertFalse(Document.search([("id", "=", self.hidden_record.id)]))

    def test_reassigning_an_activity_on_an_unreadable_document_succeeds(self):
        activity = self.hidden_activity.with_user(self.owner)
        self.assertTrue(
            activity.has_access("write"),
            "mail_activity_rule_user admits the creator/assignee",
        )
        activity.write({"user_id": self.colleague.id})
        self.assertEqual(activity.user_id, self.colleague)

    def test_the_notification_is_authored_by_the_actor_not_by_odoobot(self):
        """Sudoing the document must not silently reattribute the message."""
        activity = self.hidden_activity.with_user(self.owner)
        before = self.env["mail.message"].search([], order="id DESC", limit=1).id or 0
        activity.write({"user_id": self.colleague.id})
        posted = self.env["mail.message"].search(
            [
                ("id", ">", before),
                ("model", "=", "mail.test.multi.company.with.activity"),
                ("res_id", "=", self.hidden_record.id),
            ]
        )
        self.assertTrue(posted, "the new assignee is still notified")
        self.assertEqual(posted.author_id, self.owner.partner_id)
        self.assertIn(self.colleague.partner_id, posted.notified_partner_ids)


@tests.tagged("mail_activity")
class TestActivityChaining(TestActivityCommon):
    """Chaining is a property of the activity type, not of the document.

    The trigger branch lived inside `_action_done`'s walk over thread-backed
    documents, so a document-less activity -- the shape the systray To-Do
    creates, and the only shape a `res_model = False` type can take -- archived
    without ever creating its follow-up. Silently: no error, no log line.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.next_type = cls.env["mail.activity.type"].create(
            {"name": "Follow-up", "res_model": False}
        )
        cls.trigger_type = cls.env["mail.activity.type"].create(
            {
                "name": "Triggering",
                "res_model": False,
                "chaining_type": "trigger",
                "triggered_next_type_id": cls.next_type.id,
            }
        )

    def _activity(self, **values):
        return self.env["mail.activity"].create(
            {
                "activity_type_id": self.trigger_type.id,
                "user_id": self.env.user.id,
                "date_deadline": fields.Date.context_today(self.env["mail.activity"]),
                **values,
            }
        )

    def test_a_document_less_activity_chains(self):
        activity = self._activity(summary="my todo")
        self.assertFalse(activity.res_model)
        _messages, following = activity._action_done()
        self.assertEqual(
            following.activity_type_id,
            self.next_type,
            "the configured follow-up must be created for a To-Do too",
        )
        self.assertFalse(activity.active)

    def test_a_document_less_activity_chains_through_action_feedback(self):
        activity = self._activity(summary="my todo")
        before = (
            self.env["mail.activity"].with_context(active_test=False).search_count([])
        )
        activity.action_feedback(feedback="done")
        after = (
            self.env["mail.activity"].with_context(active_test=False).search_count([])
        )
        self.assertEqual(after - before, 1, "the Done button must chain as well")

    def test_a_thread_backed_activity_still_chains(self):
        activity = self._activity(
            res_model_id=self.env["ir.model"]._get_id("mail.test.activity"),
            res_id=self.test_record.id,
        )
        _messages, following = activity._action_done()
        self.assertEqual(following.activity_type_id, self.next_type)

    def test_a_vanished_document_does_not_chain(self):
        """A follow-up on a document that no longer exists has nowhere to live."""
        record = self.env["mail.test.activity"].create({"name": "doomed"})
        activity = self._activity(
            res_model_id=self.env["ir.model"]._get_id("mail.test.activity"),
            res_id=record.id,
        )
        self.env.flush_all()
        self.env.cr.execute(
            "DELETE FROM mail_test_activity WHERE id = %s", (record.id,)
        )
        self.env.invalidate_all()
        _messages, following = activity._action_done()
        self.assertFalse(following)
        self.assertFalse(activity.exists(), "and the stale activity is collected")


@tests.tagged("mail_activity")
class TestActivityOpenDocument(TestActivityCommon):
    def test_a_vanished_document_opens_the_no_access_form(self):
        """`has_access` answers True for an id that is no longer there.

        Reachable through a DB-level ON DELETE CASCADE, where the document's
        `unlink` override -- which would have taken the activity with it -- never
        runs; `_action_done` guards the same state and this did not.
        """
        record = self.env["mail.test.activity"].create({"name": "cascade victim"})
        activity = self.env["mail.activity"].create(
            {
                "res_model_id": self.env["ir.model"]._get_id("mail.test.activity"),
                "res_id": record.id,
                "user_id": self.env.user.id,
                "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
            }
        )
        self.env.flush_all()
        self.env.cr.execute(
            "DELETE FROM mail_test_activity WHERE id = %s", (record.id,)
        )
        self.env.invalidate_all()
        action = activity.action_view_document()
        self.assertEqual(action["res_model"], "mail.activity")
        self.assertEqual(action["res_id"], activity.id)


@tests.tagged("mail_activity")
class TestActivityGarbageCollection(TestActivityCommon):
    """Collecting garbage is not a question about the runner's access."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "GC Co B"})
        cls.runner = mail_new_test_user(
            cls.env,
            login="gc_runner",
            groups="base.group_system",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )
        Document = cls.env["mail.test.multi.company.with.activity"]
        model_id = cls.env["ir.model"]._get_id(Document._name)
        activity_type = cls.env.ref("mail.mail_activity_data_todo")
        cls.gc_activities = cls.env["mail.activity"].create(
            [
                {
                    "res_model_id": model_id,
                    "res_id": Document.create(
                        {"name": name, "company_id": company.id}
                    ).id,
                    "user_id": cls.user_employee.id,
                    "activity_type_id": activity_type.id,
                    "date_deadline": date(2015, 1, 1),
                    "summary": name,
                }
                for name, company in (
                    ("visible", cls.company_a),
                    ("hidden", cls.company_b),
                )
            ]
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "mail.activity.gc.delete_overdue_years", "1"
        )

    def test_the_gc_collects_what_the_runner_cannot_see(self):
        removed, _more = (
            self.env["mail.activity"]
            .with_user(self.runner)
            ._gc_remove_old_overdue_activities()
        )
        self.assertEqual(removed, 2)
        self.assertFalse(
            self.gc_activities.exists(),
            "an activity on a document the runner cannot read would otherwise be "
            "skipped on this run and on every later one",
        )


@tests.tagged("mail_activity")
class TestActivityStateSearch(TestActivityCommon):
    """`state` is legible in the Store payload; it must be searchable too."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        activity_type = cls.env.ref("mail.mail_activity_data_todo")
        today = cls.env["mail.activity"]._today_for(cls.env.user)
        cls.by_state = {}
        for state, deadline in (
            ("overdue", today - timedelta(days=3)),
            ("today", today),
            ("planned", today + timedelta(days=3)),
        ):
            cls.by_state[state] = cls.env["mail.activity"].create(
                {
                    "res_model_id": model_id,
                    "res_id": cls.test_record.id,
                    "user_id": cls.env.user.id,
                    "activity_type_id": activity_type.id,
                    "date_deadline": deadline,
                    "summary": state,
                }
            )
        cls.by_state["done"] = cls.env["mail.activity"].create(
            {
                "res_model_id": model_id,
                "res_id": cls.test_record.id,
                "user_id": cls.env.user.id,
                "activity_type_id": activity_type.id,
                "date_deadline": today,
                "summary": "done",
            }
        )
        cls.by_state["done"].action_feedback()

    def _found(self, domain):
        activities = (
            self.env["mail.activity"]
            .with_context(active_test=False)
            .search(domain + [("summary", "in", list(self.by_state))])
        )
        return set(activities.mapped("summary"))

    def test_each_state_is_searchable(self):
        for state in ("overdue", "today", "planned", "done"):
            with self.subTest(state=state):
                self.assertEqual(self._found([("state", "=", state)]), {state})

    def test_the_search_agrees_with_the_compute(self):
        for state, activity in self.by_state.items():
            with self.subTest(state=state):
                self.assertEqual(activity.state, state)

    def test_in_and_not_in(self):
        self.assertEqual(
            self._found([("state", "in", ["overdue", "today"])]), {"overdue", "today"}
        )
        self.assertEqual(
            self._found([("state", "not in", ["overdue", "today"])]),
            {"planned", "done"},
        )

    def test_an_unknown_state_names_nothing(self):
        """As on the document side: an unknown state matches no record."""
        self.assertEqual(self._found([("state", "=", "nonsense")]), set())
        self.assertEqual(
            self._found([("state", "not in", ["nonsense"])]),
            {"overdue", "today", "planned", "done"},
        )

    def test_an_unsupported_operator_reaches_the_caller_as_a_user_error(self):
        """The sentinel is only worth returning if the ORM acts on it.

        Asserting `_search_state` returns NotImplemented would pass whether or
        not anything downstream honours it, so drive the domain instead: the
        operator must come back as a UserError naming the field, not as the bare
        ValueError an unsearchable field used to raise out of the ORM.
        """
        for operator in ("like", "ilike", "=like", "not like", ">"):
            with self.subTest(operator=operator):
                with self.assertRaises(exceptions.UserError) as caught:
                    self.env["mail.activity"].search([("state", operator, "over")])
                self.assertIn("State", str(caught.exception))
        self.assertIs(
            self.env["mail.activity"]._search_state("like", "over"), NotImplemented
        )


@tests.tagged("mail_activity")
class TestActivitySearchOrderIsStable(TestActivityCommon):
    """Every branch of `_search` breaks ties the same way.

    The access scan and the "mine" shortcut appended `id` to the order; the
    superuser branch did not, so two admins paging the same list could see a
    row twice and another not at all whenever deadlines tied.
    """

    def test_every_branch_breaks_ties_by_id(self):
        Activity = self.env["mail.activity"]
        mine = [("user_id", "=", self.user_employee.id)]
        for label, model, domain in (
            ("superuser", Activity.sudo(), []),
            ("bypass", Activity.with_user(self.user_employee), []),
            ("mine", Activity.with_user(self.user_employee), mine),
        ):
            with self.subTest(branch=label):
                query = model._search(
                    domain, order="date_deadline", bypass_access=label == "bypass"
                )
                self.assertIn('"id"', query.order.code)


@tests.tagged("mail_activity")
class TestActivityModelSelection(TestActivityCommon):
    def test_type_and_plan_offer_the_same_models(self):
        """A type pinned to a thread model without activities is unreachable:
        no document of that model can ever carry it. Both selections read one
        helper, so they cannot drift apart again."""
        env = self.env
        type_models = env["mail.activity.type"]._fields["res_model"].get_values(env)
        plan_models = env["mail.activity.plan"]._fields["res_model"].get_values(env)
        self.assertEqual(type_models, plan_models)
        self.assertIn("mail.test.activity", type_models)
        self.assertNotIn("mail.test.simple", type_models, "a thread, no activities")
        self.assertNotIn("mail.activity.schedule", type_models, "transient")


@tests.tagged("mail_activity")
class TestActivityOneTodayPerAnswer(TestActivityCommon):
    """Every batch classification reads the clock once, not once per record.

    `_today_in_tz` reads the exact instant, so a loop that calls it per record
    can straddle a local midnight and answer two different "todays" inside one
    result. `_today_by_tz` exists to make that unrepresentable; these pin the
    callers to it, because the defect is invisible for all but a few seconds a
    day and no ordinary test would ever catch it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.deadline = cls.env["mail.activity"]._today_for(cls.env.user)
        cls.activities = cls.env["mail.activity"].create(
            [
                {
                    "res_model_id": cls.model_id,
                    "res_id": cls.test_record.id,
                    "user_id": cls.env.user.id,
                    "activity_type_id": cls.env.ref("mail.mail_activity_data_todo").id,
                    "date_deadline": cls.deadline,
                    "summary": f"same day {index}",
                }
                for index in range(12)
            ]
        )

    def _rolling_clock(self, after):
        """Answer `after` from the second call on, as a midnight would."""
        calls = {"n": 0}
        deadline = self.deadline

        def rolling(model, tz=False, moment=None):
            calls["n"] += 1
            return deadline if calls["n"] <= 1 else after

        return calls, rolling

    def test_the_activity_view_payload_carries_one_today(self):
        Activity = self.env["mail.activity"]
        _calls, rolling = self._rolling_clock(self.deadline + timedelta(days=1))
        with patch.object(type(Activity), "_today_in_tz", rolling):
            data = Activity.get_activity_data("mail.test.activity", [])
        states = {
            state
            for cells in data["grouped_activities"].values()
            for cell in cells.values()
            for state in [cell["state"], *cell["count_by_state"]]
        }
        self.assertEqual(
            len(states),
            1,
            f"one payload reported {sorted(states)} for activities that all "
            f"carry {self.deadline}",
        )

    def test_the_state_compute_carries_one_today(self):
        Activity = self.env["mail.activity"]
        self.activities.invalidate_recordset(["state"])
        _calls, rolling = self._rolling_clock(self.deadline + timedelta(days=1))
        with patch.object(type(Activity), "_today_in_tz", rolling):
            states = set(self.activities.mapped("state"))
        self.assertEqual(len(states), 1, f"one compute reported {sorted(states)}")

    def test_rescheduling_a_batch_lands_on_one_day(self):
        _calls, rolling = self._rolling_clock(self.deadline + timedelta(days=1))
        with patch.object(type(self.env["mail.activity"]), "_today_in_tz", rolling):
            self.activities.action_reschedule_today()
        self.assertEqual(
            len(set(self.activities.mapped("date_deadline"))),
            1,
            "a batch rescheduled to 'today' must land on one day",
        )

    def test_the_sql_today_case_agrees_with_its_own_else(self):
        """`_sql_today` builds a CASE from the branches and an ELSE fallback;
        read from two instants they can contradict each other."""
        Activity = self.env["mail.activity"]
        calls, rolling = self._rolling_clock(self.deadline + timedelta(days=1))
        with patch.object(type(Activity), "_today_in_tz", rolling):
            Activity._sql_today()
        self.assertEqual(
            calls["n"], 1, "_sql_today must read the clock once, not once per half"
        )


@tests.tagged("mail_activity")
class TestActivityAccessIsOneRule(TestActivityCommon):
    """`_check_access` and `_search` must answer the same question.

    Both say "mine, or the document permits it". They used to say it twice, in
    different shapes, each with its own handling of a `res_model` naming an
    uninstalled model. A security rule spelled twice is a security rule that
    drifts, so this asserts the two agree over a population built to make them
    disagree if they ever do.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "Access Co B"})
        cls.reader = mail_new_test_user(
            cls.env,
            login="access_reader",
            groups="base.group_user",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )
        cls.other = mail_new_test_user(
            cls.env, login="access_other", groups="base.group_user"
        )
        Mc = cls.env["mail.test.multi.company.with.activity"]
        todo = cls.env.ref("mail.mail_activity_data_todo")
        vals = []
        # readable document / hidden document x mine / someone else's
        for company in (cls.company_a, cls.company_b):
            document = Mc.create(
                {"name": f"doc {company.name}", "company_id": company.id}
            )
            vals.extend(
                {
                    "res_model_id": cls.env["ir.model"]._get_id(Mc._name),
                    "res_id": document.id,
                    "user_id": owner.id,
                    "activity_type_id": todo.id,
                    "summary": f"{company.name}/{owner.login}",
                }
                for owner in (cls.reader, cls.other)
            )
        # and the two document-less shapes
        vals += [
            {"user_id": cls.reader.id, "activity_type_id": todo.id, "summary": "mine"},
            {"user_id": cls.other.id, "activity_type_id": todo.id, "summary": "theirs"},
        ]
        cls.population = (
            cls.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(vals)
        )

    def test_search_and_check_access_agree_on_read(self):
        Activity = self.env["mail.activity"].with_user(self.reader)
        by_search = set(Activity.search([("id", "in", self.population.ids)]).ids)
        by_check = set(
            Activity.browse(self.population.ids)._filtered_access("read").ids
        )
        self.assertEqual(
            by_search,
            by_check,
            "the searchable set and the readable set are the same rule",
        )

    def test_the_population_is_not_trivially_all_or_nothing(self):
        """Guard the guard: a fixture everyone can read proves nothing."""
        Activity = self.env["mail.activity"].with_user(self.reader)
        visible = Activity.search([("id", "in", self.population.ids)])
        self.assertTrue(visible, "nothing visible — the fixture proves nothing")
        self.assertLess(
            len(visible),
            len(self.population),
            "everything visible — the fixture proves nothing",
        )

    def test_an_uninstalled_res_model_is_reachable_only_by_its_assignee(self):
        """Both paths treat a model that is not in the registry the same way."""
        Activity = self.env["mail.activity"]
        ghost_ids = []
        for owner in (self.reader, self.other):
            activity = Activity.create(
                {
                    "user_id": owner.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "summary": f"ghost/{owner.login}",
                }
            )
            ghost_ids.append(activity.id)
        self.env.flush_all()
        # a res_model the registry does not know, which no ORM write would allow
        self.env.cr.execute(
            "UPDATE mail_activity SET res_model = %s, res_id = %s WHERE id = ANY(%s)",
            ("gone.away.model", 1, ghost_ids),
        )
        self.env.invalidate_all()
        AsReader = Activity.with_user(self.reader)
        by_search = set(AsReader.search([("id", "in", ghost_ids)]).ids)
        by_check = set(AsReader.browse(ghost_ids)._filtered_access("read").ids)
        self.assertEqual(by_search, by_check)
        self.assertEqual(
            by_search,
            {ghost_ids[0]},
            "only the assignee reaches an activity whose model is not installed",
        )


@tests.tagged("mail_activity")
class TestActivityFilingIsAnActionOnTheDocument(TestActivityCommon):
    """Self-assignment reaches an activity; it must not authorise filing one.

    `_accessible_ids` accepted `user_id == uid` for every operation, `create`
    included, so any employee could name any record and file an activity on it.
    That was not a cosmetic hole: `create` subscribes the assignee to the
    document, and a follower may post there
    (`mail.message._discard_followed_documents`) and read what is posted
    afterwards. Measured end to end -- `message_post` raised AccessError before
    the activity and succeeded after it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "Filing Co B"})
        cls.outsider = mail_new_test_user(
            cls.env, login="filing_outsider", groups="base.group_user"
        )
        cls.model_id = cls.env["ir.model"]._get_id(
            "mail.test.multi.company.with.activity"
        )
        cls.hidden_record = cls.env["mail.test.multi.company.with.activity"].create(
            {"name": "co-B document", "company_id": cls.company_b.id}
        )
        cls.colleague = mail_new_test_user(
            cls.env, login="filing_colleague", groups="base.group_user"
        )
        cls.plain_model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        # readable by every employee, writable only by whoever created it
        cls.env["ir.access"].create(
            {
                "name": "filing: write your own mail.test.activity",
                "model_id": cls.plain_model_id,
                "group_id": cls.env.ref("base.group_user").id,
                "kind": "guard",
                "guard_scope": "members",
                "operation": "cud",
                "domain": "[('create_uid', '=', user.id)]",
            }
        )
        # The row is rolled back with the class, but `_access_domain`
        # is an ormcache on the *registry*, which a rollback does not touch --
        # so without this the entries computed while the rule existed outlive it
        # and decide access for whatever class runs next. Measured: three
        # unrelated `mail.message` tests failed in a full run and passed alone.
        cls.addClassCleanup(cls.env.registry.clear_cache)
        cls.env.registry.clear_cache()
        cls.readable = cls.env["mail.test.activity"].create({"name": "not yours"})
        cls.writable = (
            cls.env["mail.test.activity"]
            .with_user(cls.outsider)
            .create({"name": "yours"})
        )
        # followed, and then moved out of reach: following survives losing read,
        # and a follower may still post there.
        cls.aged_record = cls.env["mail.test.multi.company.with.activity"].create(
            {"name": "aged out", "company_id": cls.env.company.id}
        )
        cls.env["mail.followers"].sudo().create(
            {
                "res_model": "mail.test.multi.company.with.activity",
                "res_id": cls.aged_record.id,
                "partner_id": cls.outsider.partner_id.id,
            }
        )
        cls.aged_record.write({"company_id": cls.company_b.id})

    def _file_on_hidden(self):
        return (
            self.env["mail.activity"]
            .with_user(self.outsider)
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": self.model_id,
                    "res_id": self.hidden_record.id,
                    "user_id": self.outsider.id,
                    "activity_type_id": self.activity_type_todo.id,
                    "summary": "let me in",
                }
            )
        )

    def test_the_fixture_really_hides_the_document(self):
        Document = self.env["mail.test.multi.company.with.activity"].with_user(
            self.outsider
        )
        self.assertFalse(Document.browse(self.hidden_record.id).has_access("read"))

    def test_filing_on_an_unreachable_document_is_refused(self):
        with self.assertRaises(exceptions.AccessError):
            self._file_on_hidden()

    def test_the_refusal_leaves_no_follower_behind(self):
        with self.assertRaises(exceptions.AccessError):
            self._file_on_hidden()
        self.env.invalidate_all()
        self.assertFalse(
            self.env["mail.followers"]
            .sudo()
            .search_count(
                [
                    ("res_model", "=", "mail.test.multi.company.with.activity"),
                    ("res_id", "=", self.hidden_record.id),
                    ("partner_id", "=", self.outsider.partner_id.id),
                ]
            ),
            "a refused create must not have subscribed anybody",
        )

    def test_posting_stays_refused_after_the_attempt(self):
        """The escalation this class exists for, asserted as the user sees it."""
        document = self.env["mail.test.multi.company.with.activity"].with_user(
            self.outsider
        )
        with self.assertRaises(exceptions.AccessError):
            document.browse(self.hidden_record.id).message_post(body="before")
        with self.assertRaises(exceptions.AccessError):
            self._file_on_hidden()
        self.env.invalidate_all()
        with self.assertRaises(exceptions.AccessError):
            document.browse(self.hidden_record.id).message_post(body="after")

    def test_the_only_cell_that_moved_is_the_unreadable_one(self):
        """Filing mirrors `message_subscribe`, so only one case may change.

        Measured against HEAD on the same four documents: every cell of this
        matrix is what HEAD answers except `unreadable / self`, which HEAD
        allowed. An earlier attempt at this fix required the *write* half for
        both columns and moved three cells -- it refused an employee a reminder
        on a document they can read, and refused a follower one on a document
        they can still post to. Those two rows are here so that cannot come
        back.
        """
        for label, model_id, record, assignee, allowed in (
            ("readable/self", self.plain_model_id, self.readable, self.outsider, True),
            (
                "readable/other",
                self.plain_model_id,
                self.readable,
                self.colleague,
                False,
            ),
            ("writable/self", self.plain_model_id, self.writable, self.outsider, True),
            (
                "writable/other",
                self.plain_model_id,
                self.writable,
                self.colleague,
                True,
            ),
            ("hidden/self", self.model_id, self.hidden_record, self.outsider, False),
            ("hidden/other", self.model_id, self.hidden_record, self.colleague, False),
            ("followed/self", self.model_id, self.aged_record, self.outsider, True),
            ("followed/other", self.model_id, self.aged_record, self.colleague, False),
        ):
            with self.subTest(case=label):
                self.env.invalidate_all()
                vals = {
                    "res_model_id": model_id,
                    "res_id": record.id,
                    "user_id": assignee.id,
                    "activity_type_id": self.activity_type_todo.id,
                    "summary": label,
                }
                filing = (
                    self.env["mail.activity"]
                    .with_user(self.outsider)
                    .with_context(mail_activity_quick_update=True)
                )
                if allowed:
                    self.assertTrue(filing.create(vals).id)
                else:
                    with self.assertRaises(exceptions.AccessError):
                        filing.create(vals)

    def test_a_follower_who_can_post_can_file(self):
        """The invariant the follower half exists for: may post => may file."""
        document = self.env["mail.test.multi.company.with.activity"].with_user(
            self.outsider
        )
        self.assertFalse(document.browse(self.aged_record.id).has_access("read"))
        self.assertTrue(
            document.browse(self.aged_record.id).message_post(body="still posting")
        )

    def test_filing_on_a_reachable_document_still_works(self):
        record = (
            self.env["mail.test.activity"]
            .with_user(self.outsider)
            .create({"name": "outsider's own"})
        )
        activity = (
            self.env["mail.activity"]
            .with_user(self.outsider)
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id("mail.test.activity"),
                    "res_id": record.id,
                    "user_id": self.outsider.id,
                    "activity_type_id": self.activity_type_todo.id,
                    "summary": "mine",
                }
            )
        )
        self.assertTrue(activity.id)

    def test_a_document_less_todo_still_works(self):
        """There is no document to ask, so the shortcut still decides."""
        activity = (
            self.env["mail.activity"]
            .with_user(self.outsider)
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "user_id": self.outsider.id,
                    "activity_type_id": self.activity_type_todo.id,
                    "summary": "my own to-do",
                }
            )
        )
        self.assertTrue(activity.id)

    def test_reading_an_activity_already_filed_for_me_is_unaffected(self):
        """The systray's "Other activities" bucket depends on this."""
        activity = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": self.model_id,
                    "res_id": self.hidden_record.id,
                    "user_id": self.outsider.id,
                    "activity_type_id": self.activity_type_todo.id,
                    "summary": "assigned to you",
                }
            )
        )
        self.env.invalidate_all()
        reader = self.env["mail.activity"].with_user(self.outsider)
        self.assertTrue(reader.browse(activity.id).has_access("read"))
        self.assertIn(activity.id, reader.search([]).ids)


@tests.tagged("mail_activity")
class TestActivityChainingWithoutDocumentAccess(TestActivityCommon):
    """Completing is the assignee's right; the chained follow-up rides on it.

    `_action_done` created the follow-up unsudoed, so once `create` started
    asking the document (see `_accessible_ids`) an assignee who may finish an
    activity on a document they cannot write would have the chain die under
    them -- with an AccessError naming the activity, not anything they did.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "Chain Co B"})
        cls.assignee = mail_new_test_user(
            cls.env, login="chain_assignee", groups="base.group_user"
        )
        cls.chaining_type = cls.env["mail.activity.type"].create(
            {
                "name": "Chained",
                "chaining_type": "trigger",
                "triggered_next_type_id": cls.activity_type_todo.id,
            }
        )
        cls.record = cls.env["mail.test.multi.company.with.activity"].create(
            {"name": "co-B document", "company_id": cls.company_b.id}
        )
        cls.activity = (
            cls.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": cls.env["ir.model"]._get_id(
                        "mail.test.multi.company.with.activity"
                    ),
                    "res_id": cls.record.id,
                    "user_id": cls.assignee.id,
                    "activity_type_id": cls.chaining_type.id,
                    "summary": "chain me",
                }
            )
        )

    def test_the_fixture_really_hides_the_document(self):
        Document = self.env["mail.test.multi.company.with.activity"].with_user(
            self.assignee
        )
        self.assertFalse(Document.browse(self.record.id).has_access("read"))

    def test_a_successor_the_type_names_is_created_too(self):
        """The case the sudo is actually for, and the only one.

        Measured both ways: a follow-up carrying no `default_user_id` is
        self-assigned and needs no sudo at all -- creating the original
        subscribed the assignee, and a follower may file. One carrying a
        `default_user_id` is an activity for somebody else, needs write on the
        document, and dies with AccessError unsudoed.
        """
        successor = mail_new_test_user(
            self.env, login="chain_successor", groups="base.group_user"
        )
        next_type = self.env["mail.activity.type"].create(
            {"name": "Next, for somebody else", "default_user_id": successor.id}
        )
        chaining_type = self.env["mail.activity.type"].create(
            {
                "name": "Chained to a colleague",
                "chaining_type": "trigger",
                "triggered_next_type_id": next_type.id,
            }
        )
        activity = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id(
                        "mail.test.multi.company.with.activity"
                    ),
                    "res_id": self.record.id,
                    "user_id": self.assignee.id,
                    "activity_type_id": chaining_type.id,
                    "summary": "hand it on",
                }
            )
        )
        self.env.invalidate_all()
        activity.with_user(self.assignee).action_feedback(feedback="done")
        follow_up = (
            self.env["mail.activity"]
            .sudo()
            .search(
                [
                    ("res_id", "=", self.record.id),
                    ("previous_activity_type_id", "=", chaining_type.id),
                ]
            )
        )
        self.assertEqual(len(follow_up), 1)
        self.assertEqual(follow_up.user_id, successor)

    def test_the_assignee_can_complete_it_and_the_chain_continues(self):
        self.activity.with_user(self.assignee).action_feedback(feedback="done")
        self.env.invalidate_all()
        follow_up = (
            self.env["mail.activity"]
            .sudo()
            .search(
                [
                    ("res_id", "=", self.record.id),
                    ("previous_activity_type_id", "=", self.chaining_type.id),
                ]
            )
        )
        self.assertEqual(len(follow_up), 1, "the follow-up is still created")
        self.assertFalse(self.activity.active, "and the original is done")


@tests.tagged("mail_activity")
class TestActivityFeedbackAttachmentsVanishedDocument(ActivityScheduleCase):
    """A vanished document gets no message, so it must get no attachment copy.

    `_post_done_messages` copies the caller's attachments once per document past
    the first, because `message_post` re-parents the originals. It made the copy
    before asking whether the document was still there, so completing a batch
    over a cascade-deleted document left one orphaned `ir.attachment` behind per
    deleted document -- on the *surviving* document it was copied from.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.alive, cls.doomed = cls.env["mail.test.activity"].create(
            [{"name": "alive"}, {"name": "doomed"}]
        )
        cls.activities = (
            cls.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "res_model_id": cls.model_id,
                        "res_id": record.id,
                        "user_id": cls.env.uid,
                        "activity_type_id": cls.activity_type_todo.id,
                    }
                    for record in (cls.alive, cls.doomed)
                ]
            )
        )

    def _cascade_delete_the_doomed_document(self):
        """What an ON DELETE CASCADE leaves: the activity, without its record."""
        self.env.flush_all()
        self.env.cr.execute(
            "DELETE FROM mail_test_activity WHERE id = %s", (self.doomed.id,)
        )
        self.env.invalidate_all()

    def test_no_copy_is_made_for_the_document_that_is_gone(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "vanished.txt",
                "datas": b"aGk=",
                "res_model": "mail.compose.message",
                "res_id": 0,
            }
        )
        self._cascade_delete_the_doomed_document()
        self.activities.action_feedback(feedback="done", attachment_ids=attachment.ids)
        self.env.flush_all()
        self.assertEqual(
            self.env["ir.attachment"].search_count([("name", "=", "vanished.txt")]),
            1,
            "one attachment in, one out: the deleted document earned no copy",
        )


@tests.tagged("mail_activity")
class TestActivityStateSearchSpansTheArchived(TestActivityCommon):
    """`active` is the archive flag *and* the "done" half of `state`.

    The ORM decides its implicit `active = True` on the raw domain, where the
    only leaf it can read says `state`, so it ANDed itself onto every state
    query: `search([("state", "=", "done")])` matched nothing at all, and
    `("state", "not in", ["overdue"])` answered with two of its three remaining
    states. The field advertises four values; three were reachable.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        today = cls.env["mail.activity"]._today_for(cls.env.user)
        cls.by_state = {}
        for state, deadline in (
            ("overdue", today - timedelta(days=3)),
            ("today", today),
            ("planned", today + timedelta(days=3)),
            ("done", today),
        ):
            cls.by_state[state] = (
                cls.env["mail.activity"]
                .with_context(mail_activity_quick_update=True)
                .create(
                    {
                        "res_model_id": model_id,
                        "res_id": cls.test_record.id,
                        "user_id": cls.env.uid,
                        "activity_type_id": cls.activity_type_todo.id,
                        "date_deadline": deadline,
                        "summary": f"SPAN_{state}",
                    }
                )
            )
        cls.by_state["done"].action_feedback()

    def _found(self, domain, **context):
        activities = (
            self.env["mail.activity"]
            .with_context(**context)
            .search(domain + [("summary", "like", "SPAN\\_%")])
        )
        return set(activities.mapped("summary"))

    def test_every_advertised_state_is_reachable_from_a_default_context(self):
        for state in ("overdue", "today", "planned", "done"):
            with self.subTest(state=state):
                self.assertEqual(
                    self._found([("state", "=", state)]), {f"SPAN_{state}"}
                )

    def test_the_default_context_agrees_with_an_explicit_active_test(self):
        for domain in (
            [("state", "=", "done")],
            [("state", "not in", ["overdue"])],
            [("state", "in", ["done", "planned"])],
        ):
            with self.subTest(domain=domain):
                self.assertEqual(
                    self._found(domain), self._found(domain, active_test=False)
                )

    def test_a_domain_that_never_names_state_still_hides_the_archived(self):
        """Only a query about `state` drops the implicit filter."""
        self.assertEqual(
            self._found([]), {"SPAN_overdue", "SPAN_today", "SPAN_planned"}
        )


@tests.tagged("mail_activity")
class TestActivityCreatorCanUseWhatTheRuleGrants(TestActivityCommon):
    """`has_access` must not promise an operation the model then refuses.

    `mail_activity_rule_user` grants write and unlink on
    `['|', ('user_id','=',uid), ('create_uid','=',uid)]`, while `_accessible_ids`
    knows only the assignee. For an activity somebody created and assigned to a
    colleague, on a document the creator can no longer reach, the two disagreed:
    `has_access("write")` answered True and the write raised AccessError about
    *read* -- because `write`'s own systray bookkeeping reads `_todo_key` before
    it delegates. Which field you wrote decided whether it raised:
    `{"summary": ...}` touches none of that bookkeeping and went through,
    `{"date_deadline": ...}` is in `moves_count` and did not.

    Read stays denied here, deliberately: this is about honouring the access
    already advertised, not about widening who sees what.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_b = cls.env["res.company"].create({"name": "Creator Co B"})
        cls.creator = mail_new_test_user(
            cls.env,
            login="creator_only",
            groups="base.group_user",
            company_id=cls.env.company.id,
            company_ids=[(6, 0, [cls.env.company.id, cls.company_b.id])],
        )
        cls.colleague = mail_new_test_user(
            cls.env, login="creator_colleague", groups="base.group_user"
        )
        cls.record = cls.env["mail.test.multi.company.with.activity"].create(
            {"name": "co-B document", "company_id": cls.company_b.id}
        )
        cls.activity = (
            cls.env["mail.activity"]
            .with_user(cls.creator)
            .with_context(
                allowed_company_ids=[cls.env.company.id, cls.company_b.id],
                mail_activity_quick_update=True,
            )
            .create(
                {
                    "res_model_id": cls.env["ir.model"]._get_id(
                        "mail.test.multi.company.with.activity"
                    ),
                    "res_id": cls.record.id,
                    "user_id": cls.colleague.id,
                    "activity_type_id": cls.activity_type_todo.id,
                    "summary": "for the colleague",
                }
            )
        )
        # and then the creator loses that company, which is what makes them the
        # creator of an activity they can no longer reach through its document.
        cls.creator.write(
            {
                "company_ids": [(6, 0, [cls.env.company.id])],
                "company_id": cls.env.company.id,
            }
        )

    def _as_creator(self):
        return (
            self.env["mail.activity"].with_user(self.creator).browse(self.activity.id)
        )

    def test_the_fixture_grants_write_and_refuses_read(self):
        self.env.invalidate_all()
        self.assertFalse(self._as_creator().has_access("read"))
        self.assertTrue(self._as_creator().has_access("write"))
        self.assertTrue(self._as_creator().has_access("unlink"))

    def test_a_write_that_moves_the_badge_is_allowed_too(self):
        """The half that raised: `date_deadline` is in `moves_count`."""
        self.env.invalidate_all()
        deadline = self.env["mail.activity"]._today_for(self.colleague)
        self._as_creator().write({"date_deadline": deadline})
        self.assertEqual(self.activity.date_deadline, deadline)

    def test_every_moves_count_key_behaves_like_summary(self):
        for vals in (
            {"summary": "renamed"},
            {"date_deadline": self.env["mail.activity"]._today_for(self.colleague)},
            {"user_id": self.creator.id},
            {"active": False},
        ):
            with self.subTest(vals=vals):
                self.env.invalidate_all()
                self._as_creator().write(vals)

    def test_unlink_is_allowed(self):
        self.env.invalidate_all()
        self._as_creator().unlink()
        self.assertFalse(self.activity.exists())


@tests.tagged("mail_activity")
class TestActivityStateDomainReadsOneClock(TestActivityCommon):
    """Every branch of a state domain must count from the same day.

    `_search_state` built all four branches eagerly, each calling
    `datetime.now(UTC)` for itself, then discarded the ones not asked for. Two
    costs. `search([("state", "=", "overdue")])` read the clock **three** times
    and threw away two ~218-timezone domains; and the three reads can straddle a
    local midnight -- forced across one, the branches came back
    `[20th, 19th, 19th]`, so an activity due the 19th matched `overdue` and
    `today` at once.
    """

    def test_one_state_search_reads_the_clock_once(self):
        module = mail_activity_module
        real = module.datetime

        class Counting:
            calls = 0

            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return real.now(tz)

            def __getattr__(self, name):
                return getattr(real, name)

        for value in (["overdue"], ["overdue", "today", "planned"]):
            with self.subTest(value=value):
                Counting.calls = 0
                with patch.object(module, "datetime", Counting):
                    self.env["mail.activity"].search([("state", "in", value)])
                self.assertEqual(Counting.calls, 1)

    def test_every_branch_is_handed_the_same_instant(self):
        """Asserted where the sharing happens, not on the shape it produces.

        `_domain_deadline_today` renders `_sql_today` now, so there are no
        per-branch `user_tz` terms left to compare days between. What has to
        hold is upstream of that and survives any future shape: one `moment`
        reaches every branch, and none of them falls back to reading its own.
        """
        seen = []
        Activity = self.env["mail.activity"]
        original = type(Activity)._domain_deadline_today

        def recording(self, operator, moment=None):
            seen.append(moment)
            return original(self, operator, moment)

        with patch.object(type(Activity), "_domain_deadline_today", recording):
            Activity.search([("state", "in", ["overdue", "today", "planned"])])
        self.assertEqual(len(seen), 3, "one call per state asked for")
        self.assertNotIn(None, seen, "no branch reads its own clock")
        self.assertEqual(len(set(seen)), 1, f"one instant for all three, got {seen}")

    def test_only_the_states_asked_for_are_built(self):
        seen = []
        Activity = self.env["mail.activity"]
        original = type(Activity)._domain_deadline_today

        def recording(self, operator, moment=None):
            seen.append(operator)
            return original(self, operator, moment)

        with patch.object(type(Activity), "_domain_deadline_today", recording):
            Activity.search([("state", "=", "overdue")])
        self.assertEqual(seen, ["<"], "the other two branches are not built at all")


@tests.tagged("mail_activity")
class TestActivityDeadlineDomainInMemory(TestActivityCommon):
    """`_domain_deadline_today` renders SQL; it must also answer in memory.

    It is a `Domain.custom` now, whose predicate `DomainCustom` stores and hands
    **single records** -- `_as_predicate` returns it as-is. Written as a factory
    over the recordset it is still truthy for every record, so the domain
    matched everything, and silently: every other test drives the SQL path.
    `mixin.mail.activity._activity_state_domains` wraps this in
    `Domain("activity_ids", "any", ...)`, which `filtered_domain` on a document
    reaches, so the predicate is on a real path and not a formality.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        today = cls.env["mail.activity"]._today_for(cls.env.user)
        cls.by_state = {
            state: cls.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": model_id,
                    "res_id": cls.test_record.id,
                    "user_id": cls.env.uid,
                    "activity_type_id": cls.activity_type_todo.id,
                    "date_deadline": deadline,
                    "summary": f"MEM_{state}",
                }
            )
            for state, deadline in (
                ("overdue", today - timedelta(days=3)),
                ("today", today),
                ("planned", today + timedelta(days=3)),
            )
        }
        cls.activities = cls.env["mail.activity"].browse(
            [activity.id for activity in cls.by_state.values()]
        )

    def test_the_predicate_agrees_with_the_sql(self):
        Activity = self.env["mail.activity"]
        for operator, expected in (
            ("<", {"MEM_overdue"}),
            ("<=", {"MEM_overdue", "MEM_today"}),
            ("=", {"MEM_today"}),
            (">", {"MEM_planned"}),
            (">=", {"MEM_today", "MEM_planned"}),
        ):
            with self.subTest(operator=operator):
                domain = Activity._domain_deadline_today(operator)
                in_memory = set(
                    self.activities.filtered_domain(domain).mapped("summary")
                )
                self.assertEqual(in_memory, expected)
                in_sql = set(
                    Activity.search(
                        Domain(domain) & Domain("id", "in", self.activities.ids)
                    ).mapped("summary")
                )
                self.assertEqual(in_sql, expected)

    def test_the_document_side_filters_in_memory_too(self):
        record = self.test_record
        self.assertEqual(
            record.filtered_domain([("activity_state", "=", "overdue")]), record
        )
        self.assertFalse(record.filtered_domain([("activity_state", "=", "planned")]))


@tests.tagged("mail_activity")
class TestActivityScanShortCircuit(TestActivityCommon):
    """A domain pinned to the reader may skip the access scan, not change it.

    `_accessible_ids` admits every activity assigned to the reader outright, so
    for a domain that already restricts `user_id` to them the scan is O(match
    set) of pure agreement with the WHERE clause. `_read_group` runs it
    unbounded: measured at 20 000 activities, `_read_group` grouped by type went
    26.2 ms -> 2.7 ms against a superuser floor of 2.6, and the unpinned queries
    beside it did not move.

    The risk is that the two paths answer differently, so every test here
    compares them rather than asserting one of them.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.colleague = mail_new_test_user(
            cls.env, login="scan_colleague", groups="base.group_user"
        )
        cls.records = cls.env["mail.test.activity"].create(
            [{"name": f"Scan {index}"} for index in range(6)]
        )
        deadline = cls.env["mail.activity"]._today_for(cls.user_employee)
        cls.env["mail.activity"].with_context(mail_activity_quick_update=True).create(
            [
                {
                    "res_model_id": cls.model_id,
                    "res_id": record.id,
                    # every deadline identical, so the page is decided by the
                    # tiebreak alone -- which is the half that could differ
                    "date_deadline": deadline,
                    "user_id": (cls.user_employee if index % 2 else cls.colleague).id,
                    "activity_type_id": cls.activity_type_todo.id,
                    "summary": f"scan {index}",
                }
                for index, record in enumerate(cls.records)
            ]
        )

    def _both_paths(self, domain, **kwargs):
        """(short-circuited answer, scanned answer) for the same query."""
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        short = Activity.search(domain, **kwargs).ids
        with patch.object(
            type(Activity), "_domain_is_mine", lambda self, domain: False
        ):
            scanned = Activity.search(domain, **kwargs).ids
        return short, scanned

    def test_the_pinned_domain_is_recognised_and_an_or_branch_is_not(self):
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        uid = self.user_employee.id
        for domain, pinned in (
            ([("user_id", "=", uid)], True),
            ([("user_id", "in", [uid])], True),
            ([("user_id", "=", uid), ("active", "=", True)], True),
            (["|", ("user_id", "=", uid), ("id", ">", 0)], False),
            ([], False),
            ([("user_id", "=", self.colleague.id)], False),
        ):
            with self.subTest(domain=domain):
                self.assertIs(Activity._domain_is_mine(domain), pinned)

    def test_both_paths_return_the_same_ids_in_the_same_order(self):
        uid = self.user_employee.id
        for domain, kwargs in (
            ([("user_id", "=", uid)], {}),
            ([("user_id", "=", uid)], {"limit": 2}),
            ([("user_id", "=", uid)], {"limit": 2, "offset": 1}),
            ([("user_id", "=", uid)], {"order": "summary ASC"}),
            ([("user_id", "=", uid)], {"order": "summary ASC", "limit": 2}),
        ):
            with self.subTest(kwargs=kwargs):
                short, scanned = self._both_paths(domain, **kwargs)
                self.assertEqual(short, scanned)
                self.assertTrue(short, "the fixture must not make this vacuous")

    def test_the_pinned_search_returns_only_the_readers_own(self):
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        mine = Activity.search([("user_id", "=", self.user_employee.id)])
        self.assertTrue(mine)
        self.assertEqual(mine.user_id, self.user_employee)

    def test_the_unpinned_search_still_hides_an_unreachable_document(self):
        """The short-circuit must not be reachable from a domain it does not pin.

        The colleague's activities on documents this reader *can* read are
        legitimately visible -- `_accessible_ids` admits them -- so the case
        worth asserting is the one the scan exists for: an activity that is
        neither theirs nor on a document they can reach.
        """
        hidden_company = self.env["res.company"].create({"name": "Scan Co B"})
        hidden = self.env["mail.test.multi.company.with.activity"].create(
            {"name": "co-B", "company_id": hidden_company.id}
        )
        unreachable = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "res_model_id": self.env["ir.model"]._get_id(
                        "mail.test.multi.company.with.activity"
                    ),
                    "res_id": hidden.id,
                    "user_id": self.colleague.id,
                    "activity_type_id": self.activity_type_todo.id,
                    "summary": "not for you",
                }
            )
        )
        self.env.invalidate_all()
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        self.assertFalse(Activity._domain_is_mine([]), "the guard must not fire here")
        self.assertNotIn(unreachable.id, Activity.search([]).ids)
        self.assertNotIn(
            unreachable.id, Activity.search([("user_id", "=", self.colleague.id)]).ids
        )

    def test_the_pager_still_counts_the_match_set(self):
        """The short-circuit returns a plain Query; its count must still be right."""
        Activity = self.env["mail.activity"].with_user(self.user_employee)
        domain = [("user_id", "=", self.user_employee.id)]
        total = len(Activity.search(domain))
        query = Activity._search(domain, limit=1)
        self.assertEqual(len(query.get_result_ids()), 1)
        self.assertEqual(query.count_matching(), total)


@tests.tagged("mail_activity")
class TestActivityClockIsReproducible(ActivityScheduleCase):
    """The SQL these queries render must be the same text every run.

    `_sql_today` renders one `= ANY(ARRAY[...])` branch per calendar day in
    play, each holding the ~486 timezone names on that day. They come from
    `all_timezones()`, a frozenset, so unsorted they land in a different order
    in every process and the SQL text of every deadline and state query differs
    run to run. Not wrong, but unreproducible: a query log cannot be diffed
    against another run's and a server-side prepared statement is keyed on text.
    """

    def test_the_timezone_catalogue_comes_out_sorted(self):
        moment = datetime(2026, 8, 31, 6, 0, tzinfo=UTC)
        days = activity_calendar.days_by_timezone(activity_calendar.tz_anchor(moment))
        self.assertTrue(days, "the anchor must split the world into some days")
        self.assertEqual(
            [day for day, __ in days],
            sorted(day for day, __ in days),
            "the CASE branches must come out in a fixed order",
        )
        for day, names in days:
            with self.subTest(day=day):
                self.assertEqual(
                    list(names), sorted(names), "and so must the names inside one"
                )

    def test_the_rendered_sql_does_not_depend_on_set_iteration(self):
        """Rebuild the catalogue from a re-shuffled frozenset and compare."""
        moment = datetime(2026, 8, 31, 6, 0, tzinfo=UTC)
        Activity = self.env["mail.activity"]
        first = str(Activity._sql_today("mail_activity", moment))
        activity_calendar.days_by_timezone.cache_clear()
        second = str(Activity._sql_today("mail_activity", moment))
        self.assertEqual(
            first,
            second,
            "a rebuilt catalogue must render byte-identical SQL",
        )

    def test_the_busiest_domain_ors_its_models_in_a_fixed_order(self):
        """`_todo_keys_elsewhere` rebuilds one domain on every activity create,
        write and unlink, from a *set* of (model, id) keys. The set decided the
        order the per-model branches were OR-ed in, and `Domain.OR` preserves
        that order when the branches differ in structure -- so the busiest query
        shape on this model reached PostgreSQL as different text per worker.
        """
        Activity = self.env["mail.activity"]
        # Six models rather than three: the assertion is exact either way, but
        # against unsorted code it only fails when the set's order happens to
        # differ from sorted -- 5 of 6 permutations at three models, 719 of 720
        # at six.
        models = (
            "crm.lead",
            "mail.activity",
            "mail.test.activity",
            "mail.test.simple",
            "res.partner",
            "res.users",
        )
        keys = {(model, res_id) for model in models for res_id in range(1, 5)}
        seen = []
        origin = type(Activity).search

        def spy(records, domain, **kwargs):
            seen.append(str(domain))
            return origin(records, domain, **kwargs)

        with patch.object(type(Activity), "search", spy):
            Activity._todo_keys_elsewhere(keys)
        self.assertTrue(seen, "the bookkeeping must have issued its search")
        rendered = seen[0]
        positions = sorted(
            (rendered.index(repr(model)), model)
            for model in models
            if repr(model) in rendered
        )
        self.assertEqual(
            [model for __, model in positions],
            sorted(model for model in models if repr(model) in rendered),
            "the per-model branches must appear in sorted order, not the set's",
        )

    def test_the_bookkeeping_search_leaves_the_deadline_to_sql(self):
        """`_todo_keys_elsewhere` used to fetch every open assigned activity on
        the touched documents and drop the not-yet-due ones in Python. The
        deadline is half of `_domain_todo`, so it belongs in the query."""
        Activity = self.env["mail.activity"]
        record = self.env["mail.test.activity"].create({"name": "Doc"})
        model_id = self.env["ir.model"]._get_id("mail.test.activity")
        today = Activity._today_for(self.user_employee)
        due, __planned = Activity.create(
            [
                {
                    "res_model_id": model_id,
                    "res_id": record.id,
                    "user_id": self.user_employee.id,
                    "date_deadline": today,
                },
                {
                    "res_model_id": model_id,
                    "res_id": record.id,
                    "user_id": self.user_admin.id,
                    "date_deadline": today + timedelta(days=3),
                },
            ]
        )
        fetched = []
        origin = type(Activity).search

        def spy(records, domain, **kwargs):
            result = origin(records, domain, **kwargs)
            fetched.append(result)
            return result

        key = ("mail.test.activity", record.id)
        with patch.object(type(Activity), "search", spy):
            keys = Activity._todo_keys_elsewhere({key})
        self.assertEqual(len(fetched), 1, "one search for the bookkeeping")
        self.assertEqual(fetched[0], due, "the planned one never left PostgreSQL")
        self.assertEqual(keys, {self.user_employee: {key}})

    def test_the_state_domain_ors_its_branches_in_a_fixed_order(self):
        """`_search_state` intersects with a set; iterating it directly made
        the OR order vary per process for the same input."""
        Activity = self.env["mail.activity"]
        value = ["planned", "done", "today", "overdue"]
        rendered = [str(Activity._search_state("in", list(value))) for __ in range(5)]
        self.assertEqual(len(set(rendered)), 1, "same input, same domain")


@tests.tagged("mail_activity")
class TestActivityViewRowOrderIsStable(ActivityScheduleCase):
    """The activity view's row order must not depend on set iteration.

    `_get_activity_data_cells` unioned two dict key views into a set, and
    `_get_activity_data_order` sorts a dict built by iterating it. Python's sort
    is stable, so every tie in the sort key fell back to that set's order --
    which varies per process. Two documents due the same day came back in a
    different order in every worker, so the view reshuffled its rows between
    reloads with no data having changed.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.records = cls.env["mail.test.activity"].create(
            [{"name": f"Row {index}"} for index in range(12)]
        )

    def _schedule(self, records, deadline):
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "res_id": record.id,
                        "res_model_id": self.model_id,
                        "user_id": self.env.uid,
                        "date_deadline": deadline,
                    }
                    for record in records
                ]
            )
        )

    def test_documents_sharing_a_deadline_come_back_in_id_order(self):
        self._schedule(self.records, date(2026, 9, 9))
        self.env.flush_all()
        data = self.env["mail.activity"].get_activity_data("mail.test.activity", [])
        self.assertEqual(
            data["activity_res_ids"],
            sorted(self.records.ids),
            "every sort key ties, so the tiebreak alone decides the order",
        )

    def test_the_deadline_still_decides_when_it_differs(self):
        """The tiebreak must not have replaced the sort."""
        early, late = self.records[:6], self.records[6:]
        self._schedule(late, date(2026, 9, 1))
        self._schedule(early, date(2026, 9, 20))
        self.env.flush_all()
        data = self.env["mail.activity"].get_activity_data("mail.test.activity", [])
        self.assertEqual(
            data["activity_res_ids"],
            sorted(late.ids) + sorted(early.ids),
            "sooner deadline first, id only breaking ties within a deadline",
        )

    def test_repeated_calls_agree(self):
        self._schedule(self.records, date(2026, 9, 9))
        self.env.flush_all()
        Activity = self.env["mail.activity"]
        orders = []
        for __ in range(5):
            self.env.invalidate_all()
            orders.append(
                tuple(
                    Activity.get_activity_data("mail.test.activity", [])[
                        "activity_res_ids"
                    ]
                )
            )
        self.assertEqual(len(set(orders)), 1, "same data, same order")


@tests.tagged("mail_activity")
class TestActivityCompletionKeepsItsAttachments(ActivityScheduleCase):
    """The completion message must carry every attachment it was handed.

    An activity can own attachments of its own (``ir.attachment`` rows pointing
    at ``mail.activity``, which is what a ``many2many_binary`` widget on the
    activity form creates), and `_action_done` re-homes those onto the message
    it posts. It also posts the feedback attachments the caller passed. The
    re-homing used to *assign* the message's ``attachment_ids`` rather than add
    to it, so an activity holding both lost the feedback file from the chatter
    and left it parented to the document with no message showing it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_id = cls.env["ir.model"]._get_id("mail.test.activity")
        cls.record = cls.env["mail.test.activity"].create({"name": "Doc"})

    def _activity(self):
        return (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                {
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                    "res_id": self.record.id,
                    "res_model_id": self.model_id,
                    "user_id": self.env.uid,
                }
            )
        )

    def _owned_attachment(self, activity):
        return self.env["ir.attachment"].create(
            {
                "name": "owned.txt",
                "datas": b"b3duZWQ=",
                "res_model": "mail.activity",
                "res_id": activity.id,
            }
        )

    def _feedback_attachment(self):
        return self.env["ir.attachment"].create(
            {
                "name": "feedback.txt",
                "datas": b"ZmVlZGJhY2s=",
                "res_model": "mail.compose.message",
                "res_id": 0,
            }
        )

    def test_an_owned_attachment_does_not_evict_the_feedback_one(self):
        activity = self._activity()
        owned = self._owned_attachment(activity)
        feedback = self._feedback_attachment()
        message = self.env["mail.message"].browse(
            activity.action_feedback(feedback="done", attachment_ids=feedback.ids)
        )
        self.env.flush_all()
        self.assertEqual(
            set(message.attachment_ids.mapped("name")),
            {"owned.txt", "feedback.txt"},
            "the message shows both the activity's own file and the one the "
            "caller attached when completing it",
        )
        self.assertEqual(
            (owned.res_model, owned.res_id),
            ("mail.message", message.id),
            "the activity's own attachment is re-parented onto the message",
        )

    def test_an_owned_attachment_alone_still_lands_on_the_message(self):
        activity = self._activity()
        owned = self._owned_attachment(activity)
        message = self.env["mail.message"].browse(activity.action_feedback("done"))
        self.env.flush_all()
        self.assertEqual(message.attachment_ids, owned)

    def test_a_batch_keeps_both_kinds_on_every_message(self):
        """The two attachment paths cross only when N > 1 and each activity
        owns files: `_attachments_for_post` copies the shared one per message
        from the second post onward, while `_rehome_own_attachments` re-parents
        each activity's own. Neither may evict the other."""
        records = self.env["mail.test.activity"].create(
            [{"name": f"Batch {index}"} for index in range(3)]
        )
        activities = (
            self.env["mail.activity"]
            .with_context(mail_activity_quick_update=True)
            .create(
                [
                    {
                        "activity_type_id": self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        "res_id": record.id,
                        "res_model_id": self.model_id,
                        "user_id": self.env.uid,
                    }
                    for record in records
                ]
            )
        )
        owned = self.env["ir.attachment"].create(
            [
                {
                    "name": f"owned{index}.txt",
                    "datas": b"b3duZWQ=",
                    "res_model": "mail.activity",
                    "res_id": activity.id,
                }
                for index, activity in enumerate(activities)
            ]
        )
        shared = self._feedback_attachment()
        messages, __ = activities._action_done(
            feedback="done", attachment_ids=shared.ids
        )
        self.env.flush_all()
        self.assertEqual(len(messages), 3)
        for index, message in enumerate(messages):
            with self.subTest(message=index):
                self.assertEqual(
                    sorted(message.attachment_ids.mapped("name")),
                    sorted([f"owned{index}.txt", "feedback.txt"]),
                    "each message shows its own file and the shared one",
                )
        copies = {
            attachment.id
            for message in messages
            for attachment in message.attachment_ids
            if attachment.name == "feedback.txt"
        }
        self.assertEqual(
            len(copies), 3, "one shared attachment record per message, not one shared"
        )
        self.assertEqual(
            set(owned.mapped("res_model")),
            {"mail.message"},
            "and every owned file is re-parented onto its message",
        )

    def test_a_feedback_attachment_alone_still_lands_on_the_message(self):
        activity = self._activity()
        feedback = self._feedback_attachment()
        message = self.env["mail.message"].browse(
            activity.action_feedback(feedback="done", attachment_ids=feedback.ids)
        )
        self.env.flush_all()
        self.assertEqual(message.attachment_ids, feedback)


@tests.tagged("mail_activity")
class TestActivityDeadlineDefaultsToTheAssigneeDay(ActivityScheduleCase):
    """`create` and `default_get` must pick the same day for the same assignee.

    "Today" is the assignee's, not the server's. `default_get` reads the
    assignee out of ``default_user_id``, which is how the form action carries
    it; `create` used to read it out of the values alone, so an API create that
    let the context supply the assignee got the server's day -- filing an
    activity the assignee sees as "planned" tomorrow instead of due now.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.todo = cls.env.ref("mail.mail_activity_data_todo")
        cls.behind = mail_new_test_user(
            cls.env, login="tz_behind", groups="base.group_user", tz="Pacific/Midway"
        )
        cls.ahead = mail_new_test_user(
            cls.env, login="tz_ahead", groups="base.group_user", tz="Pacific/Kiritimati"
        )

    def _assert_agrees(self, user):
        Activity = self.env["mail.activity"].with_context(default_user_id=user.id)
        expected = Activity._today_in_tz(user.tz)
        self.assertEqual(
            Activity.default_get(["date_deadline"])["date_deadline"],
            expected,
            "the form default is the assignee's today",
        )
        self.assertEqual(
            Activity.create({"activity_type_id": self.todo.id}).date_deadline,
            expected,
            "and an API create that takes the assignee from the context agrees",
        )
        self.assertEqual(
            self.env["mail.activity"]
            .create({"activity_type_id": self.todo.id, "user_id": user.id})
            .date_deadline,
            expected,
            "and so does one that names the assignee in the values",
        )

    @freeze_time("2024-06-14 06:00:00")
    def test_a_timezone_behind_the_server(self):
        """06:00 UTC is still the 13th in Midway."""
        self._assert_agrees(self.behind)

    @freeze_time("2024-06-14 18:00:00")
    def test_a_timezone_ahead_of_the_server(self):
        """18:00 UTC is already the 15th in Kiritimati."""
        self._assert_agrees(self.ahead)

    @freeze_time("2024-06-14 06:00:00")
    def test_the_activity_is_due_today_for_its_assignee(self):
        """The point of the day: it lands in the assignee's due count."""
        activity = (
            self.env["mail.activity"]
            .with_context(default_user_id=self.behind.id)
            .create({"activity_type_id": self.todo.id})
        )
        self.assertEqual(activity.state, "today")
        self.assertEqual(activity._filtered_todo(), activity)

    @freeze_time("2024-06-14 06:00:00")
    def test_an_explicit_deadline_is_never_overridden(self):
        activity = (
            self.env["mail.activity"]
            .with_context(default_user_id=self.behind.id)
            .create(
                {
                    "activity_type_id": self.todo.id,
                    "date_deadline": date(2024, 12, 25),
                }
            )
        )
        self.assertEqual(activity.date_deadline, date(2024, 12, 25))

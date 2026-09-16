from contextlib import nullcontext
from unittest.mock import patch

from markupsafe import Markup

from odoo import Command, fields
from odoo.tests import Form, tagged, users, warmup
from odoo.tools import formataddr, mute_logger

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.mail.tools.discuss import Store


@tagged("mail_performance", "post_install", "-at_install")
class BaseMailPerformance(MailCommon, TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # standard users
        cls.user_emp_email = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email="user.emp.email@test.example.com",
            login="user_emp_email",
            groups="base.group_user,base.group_partner_manager",
            name="Ernestine Email",
            notification_type="email",
            signature="Ernestine",
        )
        cls.user_emp_inbox = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email="user.emp.inbox@test.example.com",
            login="user_emp_inbox",
            groups="base.group_user,base.group_partner_manager",
            name="Ignasse Inbox",
            notification_type="inbox",
            signature="Ignasse",
        )
        cls.user_follower_emp_email = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email="user.fol.emp.email@test.example.com",
            login="user_fol_emp_email",
            groups="base.group_user,base.group_partner_manager",
            name="Emmanuel Follower Email",
            notification_type="email",
            signature="Emmanuel",
        )
        cls.user_follower_emp_inbox = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email="user.fol.emp.inbox@test.example.com",
            login="user_fol_emp_inbox",
            groups="base.group_user,base.group_partner_manager",
            name="Isabelle Follower Inbox",
            notification_type="inbox",
            signature="Isabelle",
        )

        # portal test users
        cls.user_follower_portal = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email="user.fol.portal@test.example.com",
            login="user_fol_portal",
            groups="base.group_portal",
            name="Paul Follower Portal",
            signature="Paul",
        )
        cls.user_portal = mail_new_test_user(
            cls.env,
            company_id=cls.user_admin.company_id.id,
            company_ids=[(4, cls.user_admin.company_id.id)],
            email="user.portal@test.example.com",
            login="user_portal",
            groups="base.group_portal",
            name="Paulette Portal",
            signature="Paulette",
        )

        # customers
        cls.partner_follower = cls.env["res.partner"].create(
            {
                "country_id": cls.env.ref("base.be").id,
                "email": "partner_follower@example.com",
                "name": "partner_follower",
                "phone_ids": [
                    Command.create({"number": "04560011122", "type": "landline"})
                ],
            }
        )
        cls.customers = cls.env["res.partner"].create(
            [
                {
                    "country_id": cls.env.ref("base.be").id,
                    "email": f"customer.full.test.{idx}@example.com",
                    "name": f"Test Full Customer {idx}",
                    "phone_ids": [
                        Command.create(
                            {"number": f"045611111{idx}", "type": "landline"}
                        )
                    ],
                }
                for idx in range(5)
            ]
        )
        cls.customer = cls.customers[0]

        cls.test_attachments_vals = cls._generate_attachments_data(
            3, "mail.compose.message", 0
        )

    def setUp(self):
        super().setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, "ready", True)
        # we don't use mock_mail_gateway thus want to mock smtp to test the stack
        self._mock_smtplib_connection()
        self._mock_push_to_end_point(max_direct_push=10)

    def _create_test_records(self):
        test_record_full = (
            self.env["mail.test.ticket"]
            .with_context(self._test_context)
            .create(
                {
                    "name": "TestRecord",
                    "customer_id": self.customer.id,
                    "user_id": self.user_emp_inbox.id,
                    "email_from": "nopartner.test@example.com",
                }
            )
        )
        test_template_full = self.env["mail.template"].create(
            {
                "name": "TestTemplate",
                "model_id": self.env["ir.model"]._get("mail.test.ticket").id,
                "subject": "About {{ object.name }}",
                "body_html": '<p>Hello <t t-out="object.name"/></p>',
                "email_from": "{{ object.user_id.email_formatted }}",
                "partner_to": "{{ object.customer_id.id }}",
                "email_to": '{{ ("%s Customer <%s>" % (object.name, object.email_from)) }}',
                "attachment_ids": [
                    (0, 0, dict(attachment, res_model="mail.template"))
                    for attachment in self.test_attachments_vals
                ],
            }
        )
        self.flush_tracking()
        return test_record_full, test_template_full

    def _create_test_records_for_batch(self):
        test_partners = self.env["res.partner"].create(
            [
                {
                    "phone_ids": [
                        Command.create(
                            {"number": f"0485{idx}{idx}1122", "type": "landline"}
                        )
                    ],
                    "email": f"test.customer.{idx}@test.example.com",
                    "name": f"Test Customer {idx}",
                }
                for idx in range(10)
            ]
        )
        test_records = self.env["mail.test.ticket"].create(
            [
                {
                    "customer_id": test_partners[idx].id,
                    "email_from": test_partners[idx].email_formatted,
                    "name": f"Test Ticket {idx}",
                    "user_id": self.user_emp_inbox.id,
                }
                for idx in range(10)
            ]
        )
        test_template_full = self.env["mail.template"].create(
            {
                "name": "TestTemplate",
                "model_id": self.env["ir.model"]._get("mail.test.ticket").id,
                "subject": "About {{ object.name }}",
                "body_html": '<p>Hello <t t-out="object.name"/></p>',
                "email_from": "{{ object.user_id.email_formatted }}",
                "partner_to": "{{ object.customer_id.id }}",
                "email_to": '{{ ("%s Customer <%s>" % (object.name, object.email_from)) }}',
                "attachment_ids": [
                    (0, 0, dict(attachment, res_model="mail.template"))
                    for attachment in self.test_attachments_vals
                ],
            }
        )
        return test_partners, test_records, test_template_full


@tagged("mail_performance", "post_install", "-at_install")
class TestBaseMailPerformance(BaseMailPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.res_partner_3 = cls.env["res.partner"].create(
            {
                "name": "Gemini Furniture",
                "email": "gemini.furniture39@example.com",
            }
        )
        cls.res_partner_4 = cls.env["res.partner"].create(
            {
                "name": "Ready Mat",
                "email": "ready.mat28@example.com",
            }
        )
        cls.res_partner_10 = cls.env["res.partner"].create(
            {
                "name": "The Jackson Group",
                "email": "jackson.group82@example.com",
            }
        )
        cls.res_partner_12 = cls.env["res.partner"].create(
            {
                "name": "Azure Interior",
                "email": "azure.Interior24@example.com",
            }
        )
        cls.env["mail.performance.thread"].create(
            [
                {
                    "name": "Object 0",
                    "value": 0,
                    "partner_id": cls.res_partner_3.id,
                },
                {
                    "name": "Object 1",
                    "value": 10,
                    "partner_id": cls.res_partner_3.id,
                },
                {
                    "name": "Object 2",
                    "value": 20,
                    "partner_id": cls.res_partner_4.id,
                },
                {
                    "name": "Object 3",
                    "value": 30,
                    "partner_id": cls.res_partner_10.id,
                },
                {
                    "name": "Object 4",
                    "value": 40,
                    "partner_id": cls.res_partner_12.id,
                },
            ]
        )

    @users("admin", "demo")
    @warmup
    def test_read_mail(self):
        """Read records inheriting from 'mixin.mail.thread'."""
        records = self.env["mail.performance.thread"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=3, demo=3):
            # without cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # with cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # value_pc must have been prefetched, too
            for record in records:
                record.value_pc

    @users("admin", "demo")
    @warmup
    def test_write_mail(self):
        """Write records inheriting from 'mixin.mail.thread' (no recomputation)."""
        records = self.env["mail.performance.thread"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=2, demo=2):
            records.write({"name": "X"})

    @users("admin", "demo")
    @warmup
    def test_write_mail_with_recomputation(self):
        """Write records inheriting from 'mixin.mail.thread' (with recomputation)."""
        records = self.env["mail.performance.thread"].search([])
        self.assertEqual(len(records), 5)

        with self.assertQueryCount(admin=2, demo=2):
            records.write({"value": 42})

    @users("admin", "demo")
    @warmup
    def test_write_mail_with_tracking(self):
        """Write records inheriting from 'mixin.mail.thread' (with field tracking)."""
        record = self.env["mail.performance.thread"].create(
            {
                "name": "Test",
                "track": "Y",
                "value": 40,
                "partner_id": self.res_partner_12.id,
            }
        )

        with self.assertQueryCount(admin=3, demo=3):
            record.track = "X"

    @users("admin", "demo")
    @warmup
    def test_create_mail(self):
        """Create records inheriting from 'mixin.mail.thread' (without field tracking)."""
        model = self.env["mail.performance.thread"]

        with self.assertQueryCount(admin=2, demo=2):
            model.with_context(tracking_disable=True).create({"name": "X"})

    @users("admin", "demo")
    @warmup
    def test_create_mail_with_tracking(self):
        """Create records inheriting from 'mixin.mail.thread' (with field tracking)."""
        # +2 vs the pre-fork floor: mail.followers._add_followers wraps its
        # create in cr.savepoint(flush=False) and retries row-by-row on
        # IntegrityError, because concurrent auto-subscribes race the
        # unique(res_model, res_id, partner_id) index. SAVEPOINT + RELEASE are
        # two real queries, so every auto-subscribing create pays them.
        with self.assertQueryCount(admin=9, demo=9):
            self.env["mail.performance.thread"].create({"name": "X"})

    @users("admin", "employee")
    @warmup
    def test_create_mail_simple(self):
        # +2: the mail.followers savepoint guard (see test_create_mail_with_tracking).
        with self.assertQueryCount(admin=8, employee=8):
            self.env["mail.test.simple"].create({"name": "Test"})

    @users("admin", "employee")
    @warmup
    def test_create_mail_simple_multi(self):
        # +2: the mail.followers savepoint guard (see test_create_mail_with_tracking).
        with self.assertQueryCount(admin=8, employee=8):
            self.env["mail.test.simple"].create([{"name": "Test"}] * 5)

    @users("admin", "employee")
    @warmup
    def test_write_mail_simple(self):
        rec = self.env["mail.test.simple"].create({"name": "Test"})
        # +1 vs the pre-fork floor, all of it the ORM record-rule access check:
        # since a7450df423d rules are evaluated in Python against the records
        # (check_access -> _check_access -> filtered_domain), so a non-superuser
        # fetches whatever field the rule names when it is not already cached.
        with self.assertQueryCount(admin=1, employee=1):
            rec.write(
                {
                    "name": "Test2",
                    "email_from": "test@test.mycompany.com",
                }
            )


@tagged("mail_performance", "post_install", "-at_install")
class TestBaseAPIPerformance(BaseMailPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # automatically follow activities, for backward compatibility concerning query count
        cls.env.ref("mail.mt_activities").write({"default": True})

    @users("admin", "employee")
    @warmup
    def test_adv_activity(self):
        model = self.env["mail.test.activity"]

        # +2: the mail.followers savepoint guard (see test_create_mail_with_tracking).
        with self.assertQueryCount(admin=8, employee=8):
            model.create({"name": "Test"})

    @users("admin", "employee")
    @warmup
    @mute_logger("odoo.models.unlink")
    def test_activity_full(self):
        record = self.env["mail.test.activity"].create({"name": "Test"})
        MailActivity = self.env["mail.activity"].with_context(
            {
                "default_res_model": "mail.test.activity",
            }
        )

        with self.assertQueryCount(admin=4, employee=4):
            activity = MailActivity.create(
                {
                    "summary": "Test Activity",
                    "res_id": record.id,
                    "activity_type_id": self.env.ref("mail.mail_activity_data_todo").id,
                }
            )
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_feedback
            _category = activity.activity_type_id.category

        with self.assertQueryCount(
            admin=7, employee=7
        ):  # tm: 7 / 7  # +1: the systray to-do delta reads the records that are already due on the touched documents
            activity.action_feedback(feedback="Zizisse Done !")

    @warmup
    def test_activity_mixin_batched(self):
        """Every projected field costs the same for ten records as for one.

        Each of these computes reads the *first* activity of each record, and
        the obvious spelling of that -- ``activity_ids[:1]`` -- silently costs a
        query per record, because slicing narrows the prefetch set to the slice.
        This test pinned ``activity_date_deadline`` alone for a long time, and
        the four warm-up lines that were propping up the others could be deleted
        with the whole 908-test mail suite staying green.
        """
        records = self.env["mail.test.activity"].create([{"name": "Test"}] * 10)
        MailActivity = self.env["mail.activity"].with_context(
            {
                "default_res_model": "mail.test.activity",
            }
        )
        activity_type = self.env.ref("mail.mail_activity_data_todo")

        MailActivity.create(
            [
                {
                    "summary": "Test Activity",
                    "res_id": record.id,
                    "activity_type_id": activity_type.id,
                    "user_id": self.env.uid,
                }
                for record in records
                for _ in range(2)
            ]
        )

        for fname, expected in (
            ("activity_date_deadline", 2),
            ("activity_user_id", 2),
            ("my_activity_date_deadline", 2),
            ("activity_state", 2),
            # +1: the activity type these three read through
            ("activity_summary", 3),
            ("activity_type_id", 3),
            ("activity_type_icon", 3),
            ("activity_exception_decoration", 3),
            ("activity_exception_icon", 3),
        ):
            with self.subTest(field=fname):
                self.env.invalidate_all()
                with self.assertQueryCount(expected):
                    records.mapped(fname)

    @users("admin", "employee")
    @warmup
    @mute_logger("odoo.models.unlink")
    def test_activity_mixin(self):
        record = self.env["mail.test.activity"].create({"name": "Test"})

        with self.assertQueryCount(
            admin=7, employee=7
        ):  # +2: the to-do delta's one read, plus the res_name compute it pulls forward into the block
            activity = record.action_start("Test Start")
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_close
            _category = activity.activity_type_id.category

        record.write({"name": "Dupe write"})

        with self.assertQueryCount(
            admin=9, employee=9
        ):  # tm: 11 / 11  # +1: the systray to-do delta reads the records that are already due on the touched documents
            record.action_close("Dupe feedback")

        self.assertEqual(record.activity_ids, self.env["mail.activity"])

    @users("admin", "employee")
    @warmup
    @mute_logger("odoo.models.unlink")
    def test_activity_mixin_w_attachments(self):
        record = self.env["mail.test.activity"].create({"name": "Test"})

        attachments = self.env["ir.attachment"].create(
            [
                dict(values, res_model="mail.activity", res_id=0)
                for values in self.test_attachments_vals
            ]
        )

        with self.assertQueryCount(
            admin=7, employee=7
        ):  # +2: the to-do delta's one read, plus the res_name compute it pulls forward into the block
            activity = record.action_start("Test Start")
            # read activity_type to normalize cache between enterprise and community
            # voip module read activity_type during create leading to one less query in enterprise on action_close
            _category = activity.activity_type_id.category

        record.write({"name": "Dupe write"})

        with self.assertQueryCount(
            admin=11, employee=11
        ):  # tm 10 / 10  # +1: the systray to-do delta reads the records that are already due on the touched documents
            record.action_close("Dupe feedback", attachment_ids=attachments.ids)

        # notifications
        message = record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped("name")),
            {"AttFileName_00.txt", "AttFileName_01.txt", "AttFileName_02.txt"},
        )

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer(self):
        test_record, _test_template = self._create_test_records()
        customer_id = self.customer.id
        with self.assertQueryCount(admin=4, employee=4):
            composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                    }
                )
                .create(
                    {
                        "body": "<p>Test Body</p>",
                        "partner_ids": [(4, customer_id)],
                    }
                )
            )

        with self.assertQueryCount(admin=30, employee=30):
            composer._action_send_mail()

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_attachments(self):
        test_record, _test_template = self._create_test_records()
        customer = self.env["res.partner"].browse(self.customer.ids)
        attachments = (
            self.env["ir.attachment"]
            .with_user(self.env.user)
            .create(self.test_attachments_vals)
        )
        with self.assertQueryCount(admin=5, employee=5):
            composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                    }
                )
                .create(
                    {
                        "attachment_ids": attachments.ids,
                        "body": "<p>Test Body</p>",
                        "partner_ids": [(4, customer.id)],
                    }
                )
            )

        with self.assertQueryCount(admin=34, employee=34):
            composer._action_send_mail()

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_form_attachments(self):
        test_record, _test_template = self._create_test_records()
        customer = self.env["res.partner"].browse(self.customer.ids)
        attachments = (
            self.env["ir.attachment"]
            .with_user(self.env.user)
            .create(self.test_attachments_vals)
        )
        with self.assertQueryCount(admin=13, employee=13):
            composer_form = Form(
                self.env["mail.compose.message"].with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                    }
                )
            )
            composer_form.body = "<p>Test Body</p>"
            composer_form.partner_ids.add(customer)
            for attachment in attachments:
                composer_form.attachment_ids.add(attachment)
            composer = composer_form.save()

        with self.assertQueryCount(admin=48, employee=48):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertEqual(message.attachment_ids, attachments)
        self.assertEqual(
            message.notified_partner_ids, customer + self.user_emp_inbox.partner_id
        )

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_mass_w_template(self):
        _partners, test_records, test_template = self._create_test_records_for_batch()
        self.flush_tracking()

        with self.assertQueryCount(admin=3, employee=3):
            composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "mass_mail",
                        "default_model": test_records._name,
                        "default_res_ids": test_records.ids,
                        "default_template_id": test_template.id,
                    }
                )
                .create({})
            )

        # 79 -> 61 when _prepare_send_batch took over the per-mail pending-notification
        # search that _mark_sending used to run (and that flushed the previous mail's
        # write). The budget was 67 and this was one of the standing red pins.
        # 61 -> 51: the takeover was only half done. The snapshot is a defaultdict
        # read with .get(id), which answers None -- not [] -- for a mail it does not
        # list, and both readers treat None as "not looked up" and search anyway. So
        # every mail without a pending notification still paid for the two searches.
        # 50 -> 49: the deferred auto-delete probed `exists()` before unlinking ids
        # this same transaction had created, and that nothing between the deferral
        # and the unlink can remove -- the immediate branch of the same auto-delete
        # never probed them. One query per `_send`, so it scales with batches, not
        # with mails: `test_mail_mail_send_batch_complete` moved 14 -> 10.
        with self.assertQueryCount(admin=35, employee=35), self.mock_mail_gateway():
            composer._action_send_mail()

        self.assertEqual(len(self._new_mails), 10)

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_nodelete(self):
        test_record, _test_template = self._create_test_records()
        customer_id = self.customer.id
        with self.assertQueryCount(admin=4, employee=4):
            composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                        "mail_auto_delete": False,
                    }
                )
                .create(
                    {
                        "body": "<p>Test Body</p>",
                        "partner_ids": [(4, customer_id)],
                    }
                )
            )

        with self.assertQueryCount(admin=30, employee=30):
            composer._action_send_mail()

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_w_template(self):
        test_record, test_template = self._create_test_records()
        test_template.write({"attachment_ids": [(5, 0)]})

        with self.assertQueryCount(admin=17, employee=17):
            composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                        "default_template_id": test_template.id,
                    }
                )
                .create({})
            )

        with self.assertQueryCount(admin=31, employee=31):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertFalse(message.attachment_ids)
        new_partner = (
            self.env["res.partner"]
            .sudo()
            .search([("email", "=", "nopartner.test@example.com")])
        )
        self.assertTrue(new_partner)
        self.assertEqual(
            message.notified_partner_ids,
            self.user_emp_inbox.partner_id + self.customer + new_partner,
        )

        # remove created partner to ensure tests are the same each run
        new_partner.unlink()

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_w_template_attachments(self):
        test_record, test_template = self._create_test_records()

        with self.assertQueryCount(admin=17, employee=17):
            composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                        "default_template_id": test_template.id,
                    }
                )
                .create({})
            )

        # 41: the composer's creation wrote res_model/res_id on attachment
        # copies, fields ir.attachment's _search reads to decide visibility,
        # which emptied the user's slot of the template's attachment_ids; the
        # send reads it once more
        with self.assertQueryCount(admin=41, employee=41):
            composer._action_send_mail()

        # notifications
        message = test_record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped("name")),
            {"AttFileName_00.txt", "AttFileName_01.txt", "AttFileName_02.txt"},
        )

        # remove created partner to ensure tests are the same each run
        self.env["res.partner"].sudo().search(
            [("email", "=", "nopartner.test@example.com")]
        ).unlink()

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_w_template_form(self):
        test_record, test_template = self._create_test_records()
        test_template.write({"attachment_ids": [(5, 0)]})

        customer = self.env["res.partner"].browse(self.customer.ids)
        with self.assertQueryCount(admin=22, employee=22):
            composer_form = Form(
                self.env["mail.compose.message"].with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                        "default_template_id": test_template.id,
                    }
                )
            )
            composer = composer_form.save()

        # 49 -> 47: the author-subscribe search above, and the inbox notifier's
        # follower lookup, which `search`ed for ids and then read `res_model`,
        # `res_id` and `partner_id` off them one query later -- `search_fetch` of the
        # three fields the caller's own loop reads makes that one statement.
        with self.assertQueryCount(admin=42, employee=42):
            composer._action_send_mail()

        # notifications
        new_partner = (
            self.env["res.partner"]
            .sudo()
            .search([("email", "=", "nopartner.test@example.com")])
        )
        message = test_record.message_ids[0]
        self.assertFalse(message.attachment_ids)
        self.assertEqual(
            message.notified_partner_ids,
            customer + self.user_emp_inbox.partner_id + new_partner,
        )

        # remove created partner to ensure tests are the same each run
        new_partner.unlink()

    @users("admin", "employee")
    @warmup
    @mute_logger(
        "odoo.addons.mail.models.mail_mail", "odoo.models.unlink", "odoo.tests"
    )
    def test_mail_composer_w_template_form_attachments(self):
        test_record, test_template = self._create_test_records()

        customer = self.env["res.partner"].browse(self.customer.ids)
        with self.assertQueryCount(admin=23, employee=23):
            composer_form = Form(
                self.env["mail.compose.message"].with_context(
                    {
                        "default_composition_mode": "comment",
                        "default_model": test_record._name,
                        "default_res_ids": test_record.ids,
                        "default_template_id": test_template.id,
                    }
                )
            )
            composer = composer_form.save()

        with self.assertQueryCount(admin=60, employee=60):
            composer._action_send_mail()

        # notifications
        new_partner = (
            self.env["res.partner"]
            .sudo()
            .search([("email", "=", "nopartner.test@example.com")])
        )
        message = test_record.message_ids[0]
        self.assertEqual(
            set(message.attachment_ids.mapped("name")),
            {"AttFileName_00.txt", "AttFileName_01.txt", "AttFileName_02.txt"},
        )
        self.assertEqual(
            message.notified_partner_ids,
            customer + self.user_emp_inbox.partner_id + new_partner,
        )

        # remove created partner to ensure tests are the same each run
        new_partner.unlink()

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_message_assignation_email(self):
        # Changing the `notification_type` of a user adds or removes him a group
        # which clear the caches.
        # The @warmup decorator would then becomes useless,
        # as the first thing done by this method would be to clear the cache, making the warmup pointless.
        # So, instead of changing the user notification type within this method,
        # use another user already pre-defined with the email notification type,
        # so the ormcache is preserved.
        record = self.env["mail.test.track"].create({"name": "Test"})
        with self.assertQueryCount(admin=31, employee=30):
            record.write(
                {
                    "user_id": self.user_emp_email.id,
                }
            )

    @users("admin", "employee")
    @warmup
    def test_message_assignation_inbox(self):
        record = self.env["mail.test.track"].create({"name": "Test"})
        with self.assertQueryCount(admin=18, employee=17):
            record.write(
                {
                    "user_id": self.user_emp_inbox.id,
                }
            )

    @users("admin", "employee")
    @warmup
    def test_message_log(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})

        with self.assertQueryCount(admin=1, employee=1):
            record._message_log(
                body=Markup("<p>Test _message_log</p>"), message_type="comment"
            )

    @users("admin", "employee")
    @warmup
    def test_message_log_batch(self):
        """Logging a batch costs the same at 10 records as at 40.

        One INSERT either way: below ``COPY_THRESHOLD`` the backend inserts the
        rows in one statement. The property worth pinning is that nothing
        multiplies; ``assertQueriesConstant`` says that, and the absolute pin
        says how much the constant is.
        """
        records = self.env["mail.test.simple"].create(
            [{"name": f"Test_{idx}"} for idx in range(10)]
        )

        with self.assertQueryCount(admin=1, employee=1):
            records._message_log_batch(
                bodies={
                    record.id: Markup("<p>Test _message_log</p>") for record in records
                },
                message_type="comment",
            )

        def log_batch(size):
            more = self.env["mail.test.simple"].create(
                [{"name": f"More_{idx}"} for idx in range(size)]
            )
            more._message_log_batch(
                bodies={
                    record.id: Markup("<p>Test _message_log</p>") for record in more
                },
                message_type="comment",
            )

        self.assertQueriesConstant(log_batch, small=10, large=40)

    @users("admin", "employee")
    @warmup
    def test_message_log_with_view(self):
        """Same shape as :meth:`test_message_log_batch`, one rendered view on top.

        The extra query over the pin this replaces is the batch create's id
        pre-allocation, and it is charged once however many records are logged.
        """
        records = self.env["mail.test.simple"].create(
            [{"name": f"Test_{idx}"} for idx in range(10)]
        )

        with self.assertQueryCount(admin=3, employee=2):
            records._message_log_with_view(
                "test_mail.mail_template_simple_test",
                render_values={"partner": self.customer.with_env(self.env)},
            )

        more = self.env["mail.test.simple"].create(
            [{"name": f"More_{idx}"} for idx in range(40)]
        )
        with self.assertQueryCount(admin=1, employee=1):
            more._message_log_with_view(
                "test_mail.mail_template_simple_test",
                render_values={"partner": self.customer.with_env(self.env)},
            )

    @users("admin", "employee")
    @warmup
    def test_message_log_with_post(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})

        # +2 vs the pre-fork floor, all of it the ORM record-rule access check:
        # since a7450df423d rules are evaluated in Python against the records
        # (check_access -> _check_access -> filtered_domain), so a non-superuser
        # fetches whatever field the rule names when it is not already cached.
        with self.assertQueryCount(admin=3, employee=3):
            record.message_post(
                body=Markup("<p>Test message_post as log</p>"),
                subtype_xmlid="mail.mt_note",
                message_type="comment",
            )

    @users("admin", "employee")
    @warmup
    def test_message_post_no_notification(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})

        # +2: the ORM record-rule access check (see test_write_mail_simple).
        # 8 -> 7: `_message_post_subscribe_author` reaches `_get_get_subtypes`
        # only after reading `real_author.partner_share` and finding it False, so the
        # `partner_share = True` search that method runs when `customer_ids` is None
        # was asking the database to re-derive what the caller had just proved. The
        # caller passes the empty set it already knows.
        with self.assertQueryCount(admin=4, employee=4):
            record.message_post(
                body=Markup("<p>Test Post Performances basic</p>"),
                partner_ids=[],
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_message_post_one_email_notification(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})

        with self.assertQueryCount(admin=26, employee=25):
            record.message_post(
                body=Markup("<p>Test Post Performances with an email ping</p>"),
                partner_ids=self.customer.ids,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

    @users("admin", "employee")
    @warmup
    def test_message_post_one_inbox_notification(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})

        with self.assertQueryCount(admin=14, employee=13):
            record.message_post(
                body=Markup("<p>Test Post Performances with an inbox ping</p>"),
                partner_ids=self.user_emp_inbox.partner_id.ids,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

    @mute_logger("odoo.models.unlink")
    @users("admin", "employee")
    @warmup
    def test_message_subscribe_default(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})

        # +3: the mail.followers savepoint guard (+2, new followers are added)
        # plus one ORM record-rule access-check fetch (+1). See the sibling
        # block below for the access-check explanation.
        with self.assertQueryCount(admin=5, employee=5):
            record.message_subscribe(partner_ids=self.user_emp_inbox.partner_id.ids)

        # +1: the ORM record-rule access check (see test_write_mail_simple).
        with self.assertQueryCount(admin=2, employee=2):
            record.message_subscribe(partner_ids=self.user_emp_inbox.partner_id.ids)

    @mute_logger("odoo.models.unlink")
    @users("admin", "employee")
    @warmup
    def test_message_subscribe_subtypes(self):
        record = self.env["mail.test.simple"].create({"name": "Test"})
        subtype_ids = (
            self.env.ref("test_mail.st_mail_test_simple_external")
            | self.env.ref("mail.mt_comment")
        ).ids

        # +3: the mail.followers savepoint guard (+2, new followers are added)
        # plus one ORM record-rule access-check fetch (+1). See the sibling
        # block below for the access-check explanation.
        with self.assertQueryCount(admin=5, employee=5):
            record.message_subscribe(
                partner_ids=self.user_emp_inbox.partner_id.ids, subtype_ids=subtype_ids
            )

        # +1: the ORM record-rule access check (see test_write_mail_simple).
        with self.assertQueryCount(admin=2, employee=2):
            record.message_subscribe(
                partner_ids=self.user_emp_inbox.partner_id.ids, subtype_ids=subtype_ids
            )

    @mute_logger("odoo.models.unlink")
    @users("admin", "employee")
    @warmup
    def test_message_track(self):
        record = self.env["mail.performance.tracking"].create(
            {"name": "Zizizatestname"}
        )
        with self.assertQueryCount(admin=3, employee=3):
            record.write({"name": "Zizizanewtestname"})

        with self.assertQueryCount(admin=3, employee=3):
            record.write(
                {"field_%s" % (i): "Tracked Char Fields %s" % (i) for i in range(3)}
            )

        with self.assertQueryCount(admin=4, employee=4):
            record.write(
                {"field_%s" % (i): "Field Without Cache %s" % (i) for i in range(3)}
            )
            record.flush_recordset()
            record.write(
                {"field_%s" % (i): "Field With Cache %s" % (i) for i in range(3)}
            )

    @users("admin", "employee")
    @warmup
    def test_notification_reply_to_batch(self):
        # overwrite company name to keep it short/simple
        # and not trigger the 68 character reply_to formatting
        self.env.user.company_id.name = "Forced"
        test_records_sudo = (
            self.env["mail.test.container"]
            .sudo()
            .create(
                [
                    {
                        "alias_name": "a.%s.%d" % (self.env.user.name, index),
                        "customer_id": self.customer.id,
                        "name": "T_%d" % index,
                    }
                    for index in range(10)
                ]
            )
        )

        with self.assertQueryCount(admin=1, employee=1):
            test_records = self.env["mail.test.container"].browse(test_records_sudo.ids)
            reply_to = test_records._notify_get_reply_to(
                default=self.env.user.email_formatted,
            )

        for record in test_records:
            self.assertEqual(
                reply_to[record.id],
                formataddr(
                    (self.env.user.name, f"{record.alias_name}@{self.alias_domain}")
                ),
            )


@tagged("mail_performance", "post_install", "-at_install")
class TestMailAPIPerformance(BaseMailPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = (
            cls.env["res.users"]
            .with_context(cls._test_context)
            .create(
                {
                    "name": "Olivia Portal",
                    "login": "port",
                    "email": "p.p@example.com",
                    "signature": "--\nOlivia",
                    "notification_type": "email",
                    "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
                }
            )
        )

        cls.container = (
            cls.env["mail.test.container"]
            .with_context(mail_create_nosubscribe=True)
            .create(
                {
                    "alias_name": "test-alias",
                    "customer_id": cls.customers[0].id,
                    "name": "Test Container",
                }
            )
        )
        cls.partners = (
            cls.env["res.partner"]
            .with_context(cls._test_context)
            .create(
                [
                    {
                        "name": f"Test {idx}",
                        "email": f"test{idx}@example.com",
                    }
                    for idx in range(10)
                ]
            )
        )
        cls.container.message_subscribe(
            cls.partners.ids,
            subtype_ids=[
                cls.env.ref("mail.mt_comment").id,
                cls.env.ref("test_mail.st_mail_test_container_child_full").id,
            ],
        )

        cls.test_records_recipients = cls.env[
            "mail.performance.thread.recipients"
        ].create(
            [
                {
                    "email_from": "only.email.1@test.example.com",
                },
                {
                    "email_from": "only.email.2@test.example.com",
                },
                {
                    "email_from": "both.1@test.example.com",
                    "partner_id": cls.partners[0].id,
                },
                {
                    "email_from": "trice.1@test.example.com",
                    "partner_id": cls.partners[1].id,
                    "user_id": cls.user_admin.id,
                },
                {
                    "partner_id": cls.partners[2].id,
                },
            ]
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_mail_mail_send(self):
        message = (
            self.env["mail.message"]
            .sudo()
            .create(
                {
                    "author_id": self.env.user.partner_id.id,
                    "body": "<p>Test</p>",
                    "email_from": self.env.user.partner_id.email,
                    "message_type": "comment",
                    "model": "mail.test.container",
                    "res_id": self.container.id,
                    "subject": "Test",
                }
            )
        )
        attachments = self.env["ir.attachment"].create(
            [
                dict(
                    attachment,
                    res_id=self.container.id,
                    res_model="mail.test.container",
                )
                for attachment in self.test_attachments_vals
            ]
        )
        mail = (
            self.env["mail.mail"]
            .sudo()
            .create(
                {
                    "attachment_ids": [(4, att.id) for att in attachments],
                    "auto_delete": False,
                    "body_html": "<p>Test</p>",
                    "mail_message_id": message.id,
                    "recipient_ids": [(4, pid) for pid in self.partners.ids],
                }
            )
        )
        with self.assertQueryCount(admin=7, employee=7):
            self.env["mail.mail"].sudo().browse(mail.ids).send()

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_creation_log_is_batched(self):
        """`create()` must not spend a query per record on its creation log.

        Every other create pin in this file measures a *single* record, so one
        `message_post` per record is invisible to all of them -- which is how the
        creation log kept costing ~5 queries per record on every model that
        defines `_creation_subtype()` (crm.lead, project.task, account.move,
        hr.applicant, helpdesk.ticket) without any gate noticing.

        Measured on a container with no followers, so the number is the cost of
        *writing* the logs and not of notifying them: 5.10 queries per extra
        record before the batch, 0.10 after. Notification is still one pass per
        message -- each has its own recipients and its own rendered body -- so a
        followed container is dominated by that and would hide this regression
        again; test_tracking_subscription_create pins the followed single-record
        case.

        The assertion is on the slope, not an absolute count: unrelated drift
        moves every count together and leaves the slope alone, while a return to
        one post per record moves only the slope.
        """
        container = (
            self.env["mail.test.container"]
            .with_context(mail_create_nosubscribe=True, mail_create_nolog=True)
            .create({"name": "Unfollowed Container"})
        )
        self.assertFalse(
            container.message_partner_ids,
            "precondition: no follower, so the creation logs notify nobody",
        )
        subtype = self.env.ref("test_mail.st_mail_test_ticket_container_upd")
        counts = {}
        for size in (5, 25):
            self.env.invalidate_all()
            self.env.flush_all()
            self.env.cr.flush()
            before = self.env.cr.sql_statement_count
            records = self.env["mail.test.ticket"].create(
                [
                    {"name": f"Ticket {idx}", "container_id": container.id}
                    for idx in range(size)
                ]
            )
            self.env.flush_all()
            self.env.cr.flush()
            counts[size] = self.env.cr.sql_statement_count - before

            # cheaper is only interesting if it is unchanged: one creation log per
            # record, same subtype, same author.
            self.assertEqual(len(records.message_ids), size)
            for record in records:
                self.assertEqual(len(record.message_ids), 1)
                self.assertEqual(record.message_ids.subtype_id, subtype)
                self.assertEqual(record.message_ids.author_id, self.env.user.partner_id)

        slope = (counts[25] - counts[5]) / 20
        self.assertLess(
            slope,
            1,
            "the creation log costs %.2f queries per record (%s for 5, %s for 25): "
            "it is posting one message at a time again"
            % (slope, counts[5], counts[25]),
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_notification_write_is_batched(self):
        """`_message_post_batch` must not spend a write per message notifying it.

        Rendering an outgoing mail is per-message by nature -- its own language,
        its own recipient groups, its own body -- but *writing* it is not, and it
        was costing three statements per message: the `mail.mail` row, its
        recipient m2m, and the `mail.notification` rows.

        Measured here, with the mails actually sent, as each piece landed:

            11.75   a write pass and two read searches per message
             4.40   the three writes batched
             1.80   the References: ancestors and the tracking values batched too

        The threshold is 6, which is what this test is for: it fails at 11.75, so
        it catches a return to one `mail.mail` / `mail.notification` write per
        message, which is the regression the batching exists to prevent. It does
        not separately catch losing only the two read batches -- that needs a
        threshold under 4, and the margin against 1.80 is too thin to hold across
        a cold cache. The riskier of those two is guarded by correctness instead,
        in `test_references_are_the_same_batched_or_not`.

        1.80 is not the floor either. Sending N mails is per-mail work by
        definition. Isolated from sending, the same three changes take the batch
        from 10.28 queries per record to 0.94.

        The two assertions are different in kind and both are needed. The slope
        catches a return to one write per message. The equivalence check catches
        the failure mode the batching itself introduces -- concatenating every
        message's prepared work into one `create` and then zipping it back to the
        notification rows, where an off-by-one silently sends A's mail to B's
        followers with B's body. A count alone would call that a success.
        """
        followers = self.partners[:3]
        containers = self.env["mail.test.container"].create(
            [{"name": f"Batch Notify {idx}"} for idx in range(25)]
        )
        containers.message_subscribe(partner_ids=followers.ids)
        self.env.flush_all()

        subtype_id = self.env.ref("mail.mt_comment").id
        counts = {}
        posted = {}
        for size, offset in ((5, 0), (25, 0)):
            records = containers[offset : offset + size]
            self.env.invalidate_all()
            self.env.flush_all()
            self.env.cr.flush()
            before = self.env.cr.sql_statement_count
            # auto_delete off so the rows survive the send and can be compared:
            # with it on, a forced send unlinks every mail.mail it just created
            # and the equivalence check below would inspect an empty table.
            messages = records._message_post_batch(
                {record.id: f"<p>Body {record.id}</p>" for record in records},
                message_type="comment",
                subtype_ids={record.id: subtype_id for record in records},
                mail_auto_delete=False,
            )
            self.env.flush_all()
            self.env.cr.flush()
            counts[size] = self.env.cr.sql_statement_count - before
            posted[size] = (records, messages)

        # Each message's mail must carry that message's body and exactly that
        # message's recipients -- the concatenation must not cross entries.
        records, messages = posted[25]
        self.assertEqual(len(messages), 25)
        for record, message in zip(records, messages, strict=True):
            mails = (
                self.env["mail.mail"]
                .sudo()
                .search([("mail_message_id", "=", message.id)])
            )
            self.assertTrue(mails, "message %s notified nobody" % message.id)
            self.assertEqual(
                mails.recipient_ids,
                followers,
                "message %s went to the wrong recipients" % message.id,
            )
            for mail in mails:
                self.assertIn(f"Body {record.id}", mail.body_html or "")
            notifications = (
                self.env["mail.notification"]
                .sudo()
                .search([("mail_message_id", "=", message.id)])
            )
            self.assertEqual(notifications.res_partner_id, followers)
            self.assertEqual(
                notifications.mail_mail_id,
                mails,
                "message %s's notifications point at another message's mail"
                % message.id,
            )

        slope = (counts[25] - counts[5]) / 20
        self.assertLess(
            slope,
            6,
            "notifying costs %.2f queries per message (%s for 5, %s for 25): "
            "the mail and notification writes are back to one pass per message "
            "(1.80 when batched, 11.75 when not)" % (slope, counts[5], counts[25]),
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_mail_mail_send_batch_complete(self):
        """A more complete use case: 10 mails, attachments, servers, ... And
        2 failing emails."""
        message = (
            self.env["mail.message"]
            .sudo()
            .create(
                {
                    "author_id": self.env.user.partner_id.id,
                    "email_from": self.env.user.partner_id.email,
                    "message_type": "comment",
                    "model": "mail.test.container",
                    "res_id": self.container.id,
                    "subject": "Test",
                }
            )
        )
        attachments = self.env["ir.attachment"].create(
            [
                dict(
                    attachment,
                    res_id=self.container.id,
                    res_model="mail.test.container",
                )
                for attachment in self.test_attachments_vals
            ]
        )
        mails = (
            self.env["mail.mail"]
            .sudo()
            .create(
                [
                    {
                        "attachment_ids": [(4, att.id) for att in attachments],
                        "auto_delete": True,
                        "body_html": "<p>Test %s</p>" % idx,
                        "email_cc": "cc.1@test.example.com, cc.2@test.example.com",
                        "email_to": "customer.1@example.com, customer.2@example.com",
                        "mail_message_id": message.id,
                        "mail_server_id": self.mail_servers.ids[
                            idx % len(self.mail_servers.ids)
                        ],
                        "recipient_ids": [(4, pid) for pid in self.partners.ids],
                    }
                    for idx in range(12)
                ]
            )
        )
        mails[-2].write(
            {
                "email_cc": False,
                "email_to": "strange@example¢¡.com",
                "recipient_ids": [(5, 0)],
            }
        )
        mails[-1].write(
            {"email_cc": False, "email_to": "void", "recipient_ids": [(5, 0)]}
        )

        def _patched_unlink(records):
            nonlocal unlinked_mails
            unlinked_mails |= set(records.ids)

        unlinked_mails = set()

        # 30 -> 14, and this was one of the standing red pins at 38. 12 mails, two
        # searches each that the batch snapshot already had the answer to: the
        # snapshot is read with .get(id), which answers None for a mail it does not
        # list, and both readers take None for "not looked up".
        # 14 -> 10: `unlink` is patched out here, so the deferred auto-delete's
        # `exists()` probe was the whole cost of that step -- once per `_send`, and
        # the 12 mails split across four mail servers.
        with (
            self.assertQueryCount(admin=9, employee=9),
            self.mock_mail_gateway(),
            patch.object(type(self.env["mail.mail"]), "unlink", _patched_unlink),
        ):
            self.env["mail.mail"].sudo().browse(mails.ids).send()

        for mail in mails[:-2]:
            self.assertEqual(mail.state, "sent")
            self.assertIn(
                mail.id, unlinked_mails, "Mail: sent mails are to be unlinked"
            )
        self.assertEqual(mails[-2].state, "exception")
        self.assertIn(
            mails[-2].id,
            unlinked_mails,
            "Mail: mails with invalid recipient are also to be unlinked",
        )
        self.assertEqual(mails[-1].state, "exception")
        self.assertIn(
            mails[-1].id,
            unlinked_mails,
            "Mail: mails with invalid recipient are also to be unlinked",
        )

    @users("employee")
    @warmup
    def test_message_get_default_recipients(self):
        record = self.test_records_recipients[0].with_env(self.env)
        with self.assertQueryCount(employee=1):
            defaults = record._message_get_default_recipients()
        self.assertDictEqual(
            defaults,
            {
                record.id: {
                    "email_cc": "",
                    "email_to": "only.email.1@test.example.com",
                    "partner_ids": [],
                }
            },
        )

    @users("employee")
    @warmup
    def test_message_get_default_recipients_batch(self):
        records = self.test_records_recipients.with_env(self.env)
        with self.assertQueryCount(employee=5):
            defaults = records._message_get_default_recipients()
        self.assertDictEqual(
            defaults,
            {
                records[0].id: {
                    "email_cc": "",
                    "email_to": "only.email.1@test.example.com",
                    "partner_ids": [],
                },
                records[1].id: {
                    "email_cc": "",
                    "email_to": "only.email.2@test.example.com",
                    "partner_ids": [],
                },
                records[2].id: {
                    "email_cc": "",
                    "email_to": "",
                    "partner_ids": self.partners[0].ids,
                },
                records[3].id: {
                    "email_cc": "",
                    "email_to": "",
                    "partner_ids": self.partners[1].ids,
                },
                records[4].id: {
                    "email_cc": "",
                    "email_to": "",
                    "partner_ids": self.partners[2].ids,
                },
            },
        )

    @users("employee")
    @warmup
    def test_message_get_suggested_recipients(self):
        record = self.test_records_recipients[0].with_env(self.env)
        # +2: the ORM record-rule access check (see test_write_mail_simple).
        with self.assertQueryCount(employee=17):
            recipients = record._message_get_suggested_recipients(no_create=False)
        new_partner = self.env["res.partner"].search(
            [("email_normalized", "=", "only.email.1@test.example.com")]
        )
        self.assertEqual(len(new_partner), 1)
        self.assertDictEqual(
            recipients[0],
            {
                "email": "only.email.1@test.example.com",
                "name": "only.email.1@test.example.com",
                "partner_id": new_partner.id,
                "create_values": {},
            },
        )

    @users("employee")
    @warmup
    def test_message_get_suggested_recipients_batch(self):
        records = self.test_records_recipients.with_env(self.env)
        # -6, and the floor was already breached at 33 > 32 before it: the two
        # suggestion loops read every record's partners off a recordset union,
        # which owns no prefetch set beyond its own ids, and computed 'is_public'
        # -- a read_group over the portal and public groups -- once per record.
        # 18611cec438. Measured with test_mail alone (27, the 'tm' number) and
        # with account and marketing_card installed too (29, asserted).
        with self.assertQueryCount(employee=19):
            _recipients = records._message_get_suggested_recipients_batch(
                no_create=False
            )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_message_post_followers(self):
        self.container.message_subscribe(self.user_portal.partner_id.ids)
        record = self.container.with_user(self.env.user)

        # about 20 (19?) queries per additional customer group
        with self.assertQueryCount(admin=31, employee=30):
            record.message_post(
                body=Markup("<p>Test Post Performances</p>"),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

        self.assertEqual(record.message_ids[0].body, "<p>Test Post Performances</p>")
        self.assertEqual(
            record.message_ids[0].notified_partner_ids,
            self.partners | self.user_portal.partner_id,
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_message_post_template(self):
        self.container.message_subscribe(self.user_portal.partner_id.ids)
        record = self.container.with_user(self.env.user)
        template = self.env.ref("test_mail.mail_test_container_tpl")

        # about 20 (19 ?) queries per additional customer group
        with self.assertQueryCount(admin=47, employee=46):
            record.message_post_with_source(
                template,
                message_type="comment",
                subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                    "mail.mt_comment"
                ),
            )

        self.assertEqual(
            record.message_ids[0].body, "<p>Adding stuff on %s</p>" % record.name
        )
        self.assertEqual(
            record.message_ids[0].notified_partner_ids,
            self.partners | self.user_portal.partner_id | self.customer,
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_message_post_view(self):
        _partners, test_records, test_template = self._create_test_records_for_batch()
        self.flush_tracking()

        with self.assertQueryCount(admin=3, employee=3):
            _composer = (
                self.env["mail.compose.message"]
                .with_context(
                    {
                        "default_composition_mode": "mass_mail",
                        "default_model": test_records._name,
                        "default_res_ids": test_records.ids,
                        "default_template_id": test_template.id,
                    }
                )
                .create({})
            )

        with self.assertQueryCount(admin=8, employee=8):
            messages_as_sudo = test_records.message_post_with_source(
                "test_mail.mail_template_simple_test",
                render_values={"partner": self.user_emp_inbox.partner_id},
                subtype_id=self.env["ir.model.data"]._xmlid_to_res_id(
                    "mail.mt_comment"
                ),
            )

        self.assertEqual(len(messages_as_sudo), 10)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_message_subscribe(self):
        pids = self.partners.ids
        subtypes = self.env.ref("mail.mt_comment") | self.env.ref(
            "test_mail.st_mail_test_ticket_container_upd"
        )
        subtype_ids = subtypes.ids
        rec = self.env["mail.test.ticket"].create(
            {
                "name": "Test",
                "container_id": False,
                "customer_id": False,
                "user_id": self.user_portal.id,
            }
        )
        rec1 = rec.with_context(active_test=False)  # to see inactive records

        self.assertEqual(
            rec1.message_partner_ids,
            self.env.user.partner_id | self.user_portal.partner_id,
        )

        # subscribe new followers with forced given subtypes
        # +2: the mail.followers savepoint guard (SAVEPOINT + RELEASE). Every
        # block here widens the partner set ([:4], [:6], then all), so each one
        # does add new followers and _add_followers takes the savepoint.
        with self.assertQueryCount(admin=4, employee=4):
            rec.message_subscribe(partner_ids=pids[:4], subtype_ids=subtype_ids)

        self.assertEqual(
            rec1.message_partner_ids,
            self.env.user.partner_id | self.user_portal.partner_id | self.partners[:4],
        )

        # subscribe existing and new followers with force=False, meaning only some new followers will be added
        # +2: the mail.followers savepoint guard (SAVEPOINT + RELEASE). Every
        # block here widens the partner set ([:4], [:6], then all), so each one
        # does add new followers and _add_followers takes the savepoint.
        with self.assertQueryCount(admin=4, employee=4):
            rec.message_subscribe(partner_ids=pids[:6], subtype_ids=None)

        self.assertEqual(
            rec1.message_partner_ids,
            self.env.user.partner_id | self.user_portal.partner_id | self.partners[:6],
        )

        # subscribe existing and new followers with force=True, meaning all will have the same subtypes
        # +2: the mail.followers savepoint guard (SAVEPOINT + RELEASE). Every
        # block here widens the partner set ([:4], [:6], then all), so each one
        # does add new followers and _add_followers takes the savepoint.
        with self.assertQueryCount(admin=4, employee=4):
            rec.message_subscribe(partner_ids=pids, subtype_ids=subtype_ids)

        self.assertEqual(
            rec1.message_partner_ids,
            self.env.user.partner_id | self.user_portal.partner_id | self.partners,
        )

    @users("employee")
    @warmup
    def test_partner_find_from_emails(self):
        """Test '_partner_get_or_create_from_emails', notably to check batch optimization"""
        records = self.test_records_recipients.with_user(self.env.user)
        with self.assertQueryCount(employee=20):
            partners = records._partner_get_or_create_from_emails(
                {
                    record: [
                        record.email_from,
                        record.partner_id.email,
                        record.user_id.email,
                    ]
                    for record in records
                },
                avoid_alias=True,
                no_create=False,
            )
        new_p1 = self.env["res.partner"].search(
            [("email_normalized", "=", "only.email.1@test.example.com")]
        )
        new_p2 = self.env["res.partner"].search(
            [("email_normalized", "=", "only.email.2@test.example.com")]
        )
        new_p3 = self.env["res.partner"].search(
            [("email_normalized", "=", "both.1@test.example.com")]
        )
        new_p4 = self.env["res.partner"].search(
            [("email_normalized", "=", "trice.1@test.example.com")]
        )
        self.assertDictEqual(
            partners,
            {
                records[0].id: new_p1,
                records[1].id: new_p2,
                records[2].id: new_p3 + self.partners[0],
                records[3].id: new_p4 + self.partners[1] + self.partner_admin,
                records[4].id: self.partners[2],
            },
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_tracking_assignation(self):
        """Assignation performance test on already-created record"""
        rec = self.env["mail.test.ticket"].create(
            {
                "name": "Test",
                "container_id": self.container.id,
                "customer_id": self.customer.id,
                "user_id": self.env.uid,
            }
        )
        rec1 = rec.with_context(active_test=False)  # to see inactive records
        self.assertEqual(
            rec1.message_partner_ids, self.partners | self.env.user.partner_id
        )

        with self.assertQueryCount(admin=28, employee=28):
            rec.write({"user_id": self.user_portal.id})
        self.assertEqual(
            rec1.message_partner_ids,
            self.partners | self.env.user.partner_id | self.user_portal.partner_id,
        )
        # write tracking message
        self.assertEqual(rec1.message_ids[0].subtype_id, self.env.ref("mail.mt_note"))
        self.assertEqual(
            rec1.message_ids[0].notified_partner_ids, self.env["res.partner"]
        )
        # creation message
        self.assertEqual(
            rec1.message_ids[1].subtype_id,
            self.env.ref("test_mail.st_mail_test_ticket_container_upd"),
        )
        self.assertEqual(rec1.message_ids[1].notified_partner_ids, self.partners)
        self.assertEqual(len(rec1.message_ids), 2)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_tracking_subscription_create(self):
        """Creation performance test involving auto subscription, assignation, tracking with subtype and template send."""
        container_id = self.container.id
        customer_id = self.customer.id
        user_id = self.user_portal.id

        with self.assertQueryCount(admin=59, employee=59):
            rec = self.env["mail.test.ticket"].create(
                {
                    "name": "Test",
                    "container_id": container_id,
                    "customer_id": customer_id,
                    "user_id": user_id,
                }
            )

        rec1 = rec.with_context(active_test=False)  # to see inactive records
        self.assertEqual(
            rec1.message_partner_ids,
            self.partners | self.env.user.partner_id | self.user_portal.partner_id,
        )
        # creation message
        self.assertEqual(
            rec1.message_ids[0].subtype_id,
            self.env.ref("test_mail.st_mail_test_ticket_container_upd"),
        )
        self.assertEqual(
            rec1.message_ids[0].notified_partner_ids,
            self.partners | self.user_portal.partner_id,
        )
        self.assertEqual(len(rec1.message_ids), 1)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_tracking_subscription_subtype(self):
        """Write performance test involving auto subscription, tracking with subtype"""
        rec = self.env["mail.test.ticket"].create(
            {
                "name": "Test",
                "container_id": False,
                "customer_id": False,
                "user_id": self.user_portal.id,
            }
        )
        rec1 = rec.with_context(active_test=False)  # to see inactive records
        self.assertEqual(
            rec1.message_partner_ids,
            self.user_portal.partner_id | self.env.user.partner_id,
        )
        self.assertEqual(len(rec1.message_ids), 1)

        with self.assertQueryCount(admin=33, employee=33):
            rec.write(
                {
                    "name": "Test2",
                    "container_id": self.container.id,
                }
            )

        self.assertEqual(
            rec1.message_partner_ids,
            self.partners | self.env.user.partner_id | self.user_portal.partner_id,
        )
        # write tracking message
        self.assertEqual(
            rec1.message_ids[0].subtype_id,
            self.env.ref("test_mail.st_mail_test_ticket_container_upd"),
        )
        self.assertEqual(
            rec1.message_ids[0].notified_partner_ids,
            self.partners | self.user_portal.partner_id,
        )
        # creation message
        self.assertEqual(rec1.message_ids[1].subtype_id, self.env.ref("mail.mt_note"))
        self.assertEqual(
            rec1.message_ids[1].notified_partner_ids, self.env["res.partner"]
        )
        self.assertEqual(len(rec1.message_ids), 2)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_tracking_subscription_write(self):
        """Write performance test involving auto subscription, tracking with subtype and template send"""
        container_id = self.container.id
        customer_id = self.customer.id
        container2 = (
            self.env["mail.test.container"]
            .with_context(mail_create_nosubscribe=True)
            .create(
                {
                    "name": "Test Container 2",
                    "customer_id": False,
                    "alias_name": False,
                }
            )
        )

        rec = self.env["mail.test.ticket"].create(
            {
                "name": "Test",
                "container_id": container2.id,
                "customer_id": False,
                "user_id": self.user_portal.id,
            }
        )
        rec1 = rec.with_context(active_test=False)  # to see inactive records
        self.assertEqual(
            rec1.message_partner_ids,
            self.user_portal.partner_id | self.env.user.partner_id,
        )

        # 71 (was 62/63): the write's tracking message now correctly notifies the
        # container followers it just auto-subscribed (the assertions below), which
        # creates their notifications + bus fan-out. Previously a flushing savepoint
        # in _add_followers ran _track_finalize before those followers existed,
        # so only the assignee was notified (fewer queries, wrong result).
        with self.assertQueryCount(admin=32, employee=32):
            rec.write(
                {
                    "name": "Test2",
                    "container_id": container_id,
                    "customer_id": customer_id,
                }
            )

        self.assertEqual(
            rec1.message_partner_ids,
            self.partners | self.env.user.partner_id | self.user_portal.partner_id,
        )
        # write tracking message
        self.assertEqual(
            rec1.message_ids[0].subtype_id,
            self.env.ref("test_mail.st_mail_test_ticket_container_upd"),
        )
        self.assertEqual(
            rec1.message_ids[0].notified_partner_ids,
            self.partners | self.user_portal.partner_id,
        )
        # creation message
        self.assertEqual(
            rec1.message_ids[1].subtype_id,
            self.env.ref("test_mail.st_mail_test_ticket_container_upd"),
        )
        self.assertEqual(
            rec1.message_ids[1].notified_partner_ids, self.user_portal.partner_id
        )
        self.assertEqual(len(rec1.message_ids), 2)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("admin", "employee")
    @warmup
    def test_tracking_template(self):
        """Write performance test involving assignation, tracking with template"""
        customer_id = self.customer.id
        self.assertTrue(
            self.env.registry.ready, "We need to simulate that registery is ready"
        )
        rec = self.env["mail.test.ticket"].create(
            {
                "name": "Test",
                "container_id": self.container.id,
                "customer_id": False,
                "user_id": self.user_portal.id,
                "mail_template": self.env.ref(
                    "test_mail.mail_test_ticket_tracking_tpl"
                ).id,
            }
        )
        rec1 = rec.with_context(active_test=False)  # to see inactive records
        self.assertEqual(
            rec1.message_partner_ids,
            self.partners | self.env.user.partner_id | self.user_portal.partner_id,
        )

        with self.assertQueryCount(admin=28, employee=28):
            rec.write(
                {
                    "name": "Test2",
                    "customer_id": customer_id,
                    "user_id": self.env.uid,
                }
            )

        # write template message (sent to customer, mass mailing kept for history)
        self.assertEqual(
            rec1.message_ids[0].subtype_id, self.env["mail.message.subtype"]
        )
        self.assertEqual(rec1.message_ids[0].subject, "Test Template")
        # write tracking message
        self.assertEqual(rec1.message_ids[1].subtype_id, self.env.ref("mail.mt_note"))
        self.assertEqual(
            rec1.message_ids[1].notified_partner_ids, self.env["res.partner"]
        )
        # creation message
        self.assertEqual(
            rec1.message_ids[2].subtype_id,
            self.env.ref("test_mail.st_mail_test_ticket_container_upd"),
        )
        self.assertEqual(
            rec1.message_ids[2].notified_partner_ids,
            self.partners | self.user_portal.partner_id,
        )
        self.assertEqual(len(rec1.message_ids), 3)


@tagged("mail_performance", "WIP", "post_install", "-at_install")
class TestMailAccessPerformance(BaseMailPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.records_access = cls.env["mail.test.access"].create(
            [
                {"name": "Access.1", "access": "public"},
                {"name": "Access.2", "access": "logged"},
                {"name": "Access.3", "access": "followers"},
            ]
        )
        cls.records_access_custo = cls.env["mail.test.access.custo"].create(
            [
                {"name": "Custo.1"},
                {
                    "name": "Custo.2",
                    "is_readonly": True,
                },  # read access, should be able to read messages / activities
                {
                    "name": "Custo.3",
                    "is_locked": True,
                },  # not able to read messages / activities
            ]
        )
        cls.records_mc = cls.env["mail.test.multi.company"].create(
            [
                {"name": "MC.1"},
                {"name": "MC.2"},
                {"name": "MC.3"},
            ]
        )

        # messages to check access
        cls.messages = cls.env["mail.message"]
        for records_model in [
            cls.records_access,
            cls.records_access_custo,
            cls.records_mc,
        ]:
            for record in records_model:
                cls.messages += record.with_user(cls.user_admin).message_post(
                    body=f"Posting on {record.name}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )
        # message employee cannot read due to specific rules (aka locked record)
        cls.messages_emp_nope = cls.messages[5]

        # activities to check access
        cls.activities = cls.env["mail.activity"]
        for records_model in [
            cls.records_access,
            cls.records_access_custo,
            cls.records_mc,
        ]:
            cls.activities += cls.env["mail.activity"].create(
                [
                    {
                        "res_id": record.id,
                        "res_model_id": cls.env["ir.model"]._get_id(record._name),
                        "summary": f"TestActivity {idx} on {record._name},{record.id} for {user.name}",
                        "user_id": user.id,
                    }
                    for record in records_model
                    for user in (cls.user_admin + cls.user_employee)
                    for idx in range(2)
                ]
            )
            records_model.message_unsubscribe(
                partner_ids=(cls.user_admin + cls.user_employee).partner_id.ids
            )
        # activities employee cannot read due to specific rules (other user on non open custo)
        cls.activities_emp_nope = cls.activities.filtered(
            lambda a: (
                a.res_model == "mail.test.access.custo"
                and a.res_id == cls.records_access_custo[2].id
                and a.user_id == cls.user_admin
            )
        )

    @users("employee")
    @warmup
    def test_activity_read(self):
        # queries
        # fetch activities: 1
        # filter records: 3 (1 / model)
        # '_fetch_query': 1
        profile = self.profile() if self.warm else nullcontext()
        with self.assertQueryCount(employee=5), profile:
            content = (
                (self.activities - self.activities_emp_nope)
                .with_env(self.env)
                .read(["summary"])
            )
        self.assertEqual(len(content), len(self.activities - self.activities_emp_nope))

    @users("employee")
    @warmup
    def test_activity_search(self):
        # queries
        # select mail.activity: 1
        # filter records: 3 (1 / model)
        profile = self.profile() if self.warm else nullcontext()
        with self.assertQueryCount(employee=4), profile:
            found = self.activities.with_env(self.env).search(
                [("summary", "ilike", "TestActivity")]
            )
        self.assertEqual(found, self.activities - self.activities_emp_nope)

    @users("employee")
    @warmup
    def test_message_read(self):
        # queries
        # fetch messages: 1
        # filter records: 3 (1 / model)
        # 'read': 1
        profile = self.profile() if self.warm else nullcontext()
        with self.assertQueryCount(employee=5), profile:
            content = (
                (self.messages - self.messages_emp_nope)
                .with_env(self.env)
                .read(["body"])
            )
        self.assertEqual(len(content), len(self.messages - self.messages_emp_nope))

    @users("employee")
    @warmup
    def test_message_search(self):
        # queries
        # select mail.message: 1
        # filter records: 3 (1 / model)
        profile = self.profile() if self.warm else nullcontext()
        with self.assertQueryCount(employee=4), profile:
            found = self.messages.with_env(self.env).search(
                [("body", "ilike", "Posting on ")]
            )
        self.assertEqual(found, self.messages - self.messages_emp_nope)


@tagged("mail_performance", "mail_store", "post_install", "-at_install")
class TestMessageToStorePerformance(BaseMailPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.containers = (
            cls.env["mail.test.container"]
            .with_context(mail_create_nosubscribe=True)
            .create(
                [
                    {
                        "alias_name": "test-alias",
                        "customer_id": cls.customers[0].id,
                        "name": "Test Container",
                    },
                    {
                        "alias_name": "test-alias-2",
                        "customer_id": cls.customers[1].id,
                        "name": "Test Container 2",
                    },
                ]
            )
        )
        cls.partners = (
            cls.env["res.partner"]
            .with_context(cls._test_context)
            .create(
                [
                    {
                        "name": f"Test {idx}",
                        "email": f"test{idx}@example.com",
                    }
                    for idx in range(10)
                ]
            )
        )
        cls.containers.message_subscribe(
            cls.partners.ids,
            subtype_ids=[
                cls.env.ref("mail.mt_comment").id,
                cls.env.ref("test_mail.st_mail_test_container_child_full").id,
            ],
        )
        cls.container = cls.containers[0]

        name_field = cls.env["ir.model.fields"]._get(cls.container._name, "name")
        customer_id_field = cls.env["ir.model.fields"]._get(
            cls.container._name, "customer_id"
        )
        comment_subtype_id = cls.env["ir.model.data"]._xmlid_to_res_id(
            "mail.mt_comment"
        )

        cls.link_previews = cls.env["mail.link.preview"].create(
            [
                {"source_url": "https://www.odoo.com"},
                {"source_url": "https://www.example.com"},
            ]
        )

        cls.messages_all = (
            cls.env["mail.message"]
            .sudo()
            .create(
                [
                    {
                        "attachment_ids": [
                            (
                                0,
                                0,
                                {
                                    "datas": "data",
                                    "name": f"Test file {att_idx}",
                                    "res_id": record.id,
                                    "res_model": record._name,
                                },
                            )
                            for att_idx in range(2)
                        ],
                        "author_id": cls.partners[msg_idx].id,
                        "body": f"<p>Test {msg_idx}</p>",
                        "email_from": cls.partners[msg_idx].email_formatted,
                        "message_link_preview_ids": [
                            Command.create(
                                {"link_preview_id": cls.link_previews[0].id}
                            ),
                            Command.create(
                                {"link_preview_id": cls.link_previews[1].id}
                            ),
                        ],
                        "message_type": "comment",
                        "model": record._name,
                        "notification_ids": [
                            (
                                0,
                                0,
                                {
                                    "is_read": False,
                                    "notification_type": "inbox",
                                    "res_partner_id": cls.partners[
                                        (record_idx * 5) + (msg_idx * 2)
                                    ].id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "is_read": True,
                                    "notification_type": "email",
                                    "notification_status": "sent",
                                    "res_partner_id": cls.partners[
                                        (record_idx * 5) + (msg_idx * 2) + 1
                                    ].id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "is_read": True,
                                    "notification_type": "email",
                                    "notification_status": "exception",
                                    "res_partner_id": cls.partners[
                                        (record_idx * 5) + (msg_idx * 2) + 2
                                    ].id,
                                },
                            ),
                        ],
                        "partner_ids": [
                            (4, cls.partners[(record_idx * 5) + msg_idx].id),
                            (4, cls.partners[(record_idx * 5) + msg_idx + 1].id),
                        ],
                        "reaction_ids": [
                            (
                                0,
                                0,
                                {
                                    "content": "\U0001f4e7",
                                    "partner_id": cls.partners[(record_idx * 5)].id,
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "content": "\U0001f4e8",
                                    "partner_id": cls.partners[(record_idx * 5) + 1].id,
                                },
                            ),
                        ],
                        "res_id": record.id,
                        "starred_partner_ids": [
                            (4, cls.partners[(record_idx * 5) + msg_idx].id),
                            (4, cls.partners[(record_idx * 5) + (msg_idx * 2) + 1].id),
                        ],
                        "subject": f"Test Container {msg_idx}",
                        "subtype_id": comment_subtype_id,
                        "tracking_value_ids": [
                            (
                                0,
                                0,
                                {
                                    "field_id": name_field.id,
                                    "new_value_char": "new 0",
                                    "old_value_char": "old 0",
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "field_id": customer_id_field.id,
                                    "new_value_char": "new 1",
                                    "new_value_integer": cls.partners[
                                        (record_idx * 5)
                                    ].id,
                                    "old_value_char": "old 1",
                                    "old_value_integer": cls.partners[
                                        (record_idx * 5) + 1
                                    ].id,
                                },
                            ),
                        ],
                    }
                    for msg_idx in range(2)
                    for record_idx, record in enumerate(cls.containers)
                ]
            )
        )

    def test_assert_initial_values(self):
        self.assertEqual(len(self.messages_all), 2 * 2)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_message_to_store_multi(self):
        """Test performance of `_to_store` with multiple messages with multiple attachments,
        different authors, various notifications, and different tracking values.

        Those messages might not make sense functionally but they are crafted to
        cover as much of the code as possible in regard to number of queries.

        Setup :
          * 2 records (self.containers -> 2 mail.test.container record, with
            a different customer_id each)
          * 2 messages / record
          * 2 attachments / message
          * 3 notifications / message
          * 2 tracking values / message
        """
        messages_all = self.messages_all.with_env(self.env)

        with self.assertQueryCount(employee=23):
            res = Store().add(messages_all).get_result()

        self.assertEqual(len(res["mail.message"]), 2 * 2)
        for message in res["mail.message"]:
            self.assertEqual(len(message["attachment_ids"]), 2)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_message_to_store_single(self):
        message = self.messages_all[0].with_env(self.env)

        with self.assertQueryCount(employee=23):
            res = Store().add(message).get_result()

        self.assertEqual(len(res["mail.message"]), 1)
        self.assertEqual(len(res["mail.message"][0]["attachment_ids"]), 2)

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_message_to_store_group_thread_name_by_model(self):
        """Ensures the fetch of multiple thread names is grouped by model."""
        records = [
            self.env["mail.test.simple"].create({"name": "Test"}) for _i in range(5)
        ]
        records.append(self.env["mail.test.track"].create({"name": "Test"}))

        messages = self.env["mail.message"].create(
            [{"model": record._name, "res_id": record.id} for record in records]
        )

        with self.assertQueryCount(employee=2):
            res = Store().add(messages).get_result()
            self.assertEqual(len(res["mail.message"]), 6)

        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(employee=12):
            res = Store().add(messages).get_result()
            self.assertEqual(len(res["mail.message"]), 6)

    @warmup
    def test_message_to_store_multi_followers_inbox(self):
        """Test query count as well as bus notifcations from sending a message to multiple followers
        with inbox."""
        record = self.env["mail.test.simple"].create({"name": "Test"})
        record.message_partner_ids = (
            self.user_emp_inbox + self.user_follower_emp_inbox
        ).partner_id
        follower_1 = record.message_follower_ids.filtered(
            lambda f: f.partner_id == self.user_emp_inbox.partner_id
        )
        follower_2 = record.message_follower_ids.filtered(
            lambda f: f.partner_id == self.user_follower_emp_inbox.partner_id
        )

        def get_bus_params():
            # The inbox fan-out carries no `notification_ids` and no
            # `mail.notification`: `_get_store_defaults_fields` drops them under
            # `mail_notify_inbox`, so each recipient stops receiving a record
            # per *other* recipient -- O(recipients^2) payload, and every one of
            # them naming an email address that recipient may not read. The two
            # recipient partners left with them: they were in this payload only
            # because the notification records referenced them.
            # `mail/tests/test_mail_audit_v6b.py` pins both halves.
            message = self.env["mail.message"].search([], order="id desc", limit=1)
            return (
                [
                    (self.cr.dbname, "res.partner", self.user_emp_inbox.partner_id.id),
                    (
                        self.cr.dbname,
                        "res.partner",
                        self.user_follower_emp_inbox.partner_id.id,
                    ),
                ],
                [
                    {
                        "type": "mail.message/inbox",
                        "payload": {
                            "message_id": message.id,
                            "store_data": {
                                "mail.followers": [
                                    {
                                        "id": follower_1.id,
                                        "is_active": True,
                                        "partner_id": self.user_emp_inbox.partner_id.id,
                                    },
                                ],
                                "mail.message": self._filter_messages_fields(
                                    {
                                        "attachment_ids": [],
                                        "author_guest_id": False,
                                        "author_id": self.env.user.partner_id.id,
                                        "body": [
                                            "markup",
                                            "<p>Test Post Performances with multiple inbox ping!</p>",
                                        ],
                                        "create_date": fields.Datetime.to_string(
                                            message.create_date
                                        ),
                                        "date": fields.Datetime.to_string(message.date),
                                        "default_subject": "Test",
                                        "email_from": '"OdooBot" <odoobot@example.com>',
                                        "id": message.id,
                                        "incoming_email_cc": False,
                                        "incoming_email_to": False,
                                        "message_link_preview_ids": [],
                                        "message_type": "comment",
                                        "model": "mail.test.simple",
                                        "needaction": True,
                                        "partner_ids": [],
                                        "pinned_at": False,
                                        "rating_id": False,
                                        "reactions": [],
                                        "record_name": "Test",
                                        "res_id": record.id,
                                        "scheduledDatetime": False,
                                        "starred": False,
                                        "subject": False,
                                        "subtype_id": self.env.ref(
                                            "mail.mt_comment"
                                        ).id,
                                        "thread": {
                                            "id": record.id,
                                            "model": "mail.test.simple",
                                        },
                                        "trackingValues": [],
                                        "write_date": fields.Datetime.to_string(
                                            message.write_date
                                        ),
                                    },
                                ),
                                "mail.message.subtype": [
                                    {
                                        "description": False,
                                        "id": self.env.ref("mail.mt_comment").id,
                                    },
                                ],
                                "mixin.mail.thread": self._filter_threads_fields(
                                    {
                                        "display_name": "Test",
                                        "has_mail_thread": True,
                                        "id": record.id,
                                        "model": "mail.test.simple",
                                        "module_icon": "/base/static/description/icon.png",
                                        "selfFollower": follower_1.id,
                                    },
                                ),
                                "res.partner": self._filter_partners_fields(
                                    {
                                        "avatar_128_access_token": self.env.user.partner_id._get_avatar_128_access_token(),
                                        "id": self.env.user.partner_id.id,
                                        "is_company": False,
                                        "main_user_id": self.env.user.id,
                                        "name": "OdooBot",
                                        "write_date": fields.Datetime.to_string(
                                            self.env.user.partner_id.write_date
                                        ),
                                    },
                                ),
                                "res.users": self._filter_users_fields(
                                    {
                                        "id": self.env.user.id,
                                        "partner_id": self.env.user.partner_id.id,
                                        "share": False,
                                    },
                                ),
                            },
                        },
                    },
                    {
                        "type": "mail.message/inbox",
                        "payload": {
                            "message_id": message.id,
                            "store_data": {
                                "mail.followers": [
                                    {
                                        "id": follower_2.id,
                                        "is_active": True,
                                        "partner_id": self.user_follower_emp_inbox.partner_id.id,
                                    },
                                ],
                                "mail.message": self._filter_messages_fields(
                                    {
                                        "attachment_ids": [],
                                        "author_guest_id": False,
                                        "author_id": self.env.user.partner_id.id,
                                        "body": [
                                            "markup",
                                            "<p>Test Post Performances with multiple inbox ping!</p>",
                                        ],
                                        "create_date": fields.Datetime.to_string(
                                            message.create_date
                                        ),
                                        "date": fields.Datetime.to_string(message.date),
                                        "default_subject": "Test",
                                        "email_from": '"OdooBot" <odoobot@example.com>',
                                        "id": message.id,
                                        "incoming_email_cc": False,
                                        "incoming_email_to": False,
                                        "message_link_preview_ids": [],
                                        "message_type": "comment",
                                        "model": "mail.test.simple",
                                        "needaction": True,
                                        "partner_ids": [],
                                        "pinned_at": False,
                                        "rating_id": False,
                                        "reactions": [],
                                        "record_name": "Test",
                                        "res_id": record.id,
                                        "scheduledDatetime": False,
                                        "starred": False,
                                        "subject": False,
                                        "subtype_id": self.env.ref(
                                            "mail.mt_comment"
                                        ).id,
                                        "thread": {
                                            "id": record.id,
                                            "model": "mail.test.simple",
                                        },
                                        "trackingValues": [],
                                        "write_date": fields.Datetime.to_string(
                                            message.write_date
                                        ),
                                    },
                                ),
                                "mail.message.subtype": [
                                    {
                                        "description": False,
                                        "id": self.env.ref("mail.mt_comment").id,
                                    },
                                ],
                                "mixin.mail.thread": self._filter_threads_fields(
                                    {
                                        "display_name": "Test",
                                        "has_mail_thread": True,
                                        "id": record.id,
                                        "model": "mail.test.simple",
                                        "module_icon": "/base/static/description/icon.png",
                                        "selfFollower": follower_2.id,
                                    },
                                ),
                                "res.partner": self._filter_partners_fields(
                                    {
                                        "avatar_128_access_token": self.env.user.partner_id._get_avatar_128_access_token(),
                                        "id": self.env.user.partner_id.id,
                                        "is_company": False,
                                        "main_user_id": self.env.user.id,
                                        "name": "OdooBot",
                                        "write_date": fields.Datetime.to_string(
                                            self.env.user.partner_id.write_date
                                        ),
                                    },
                                ),
                                "res.users": self._filter_users_fields(
                                    {
                                        "id": self.env.user.id,
                                        "partner_id": self.env.user.partner_id.id,
                                        "share": False,
                                    },
                                ),
                            },
                        },
                    },
                ],
            )

        self.env.invalidate_all()
        with self.assertBus(get_params=get_bus_params):
            # 18 -> 17: nobody here receives this post by email, and the batch
            # notify path no longer prefetches the References ancestors and the
            # tracking values that only `_notify_by_email_prepare` reads -- it
            # returns on the first line when no recipient is `notif == "email"`.
            with self.assertQueryCount(14):
                record.message_post(
                    body=Markup(
                        "<p>Test Post Performances with multiple inbox ping!</p>"
                    ),
                    message_type="comment",
                    subtype_xmlid="mail.mt_comment",
                )


class BaseMailPostPerformance(BaseMailPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # records
        cls.record_container = cls.env["mail.test.container"].create(
            {
                "name": "Test record",
                "customer_id": cls.customer.id,
                "alias_name": "test-alias",
            }
        )
        _partners, cls.record_tickets, _test_template = (
            cls._create_test_records_for_batch(cls)
        )
        # avoid hanging followers, like assigned users (user_id)
        cls.env["mail.followers"].search(
            [
                ("res_model", "=", cls.record_tickets._name),
                ("res_id", "in", cls.record_tickets.ids),
            ]
        ).unlink()
        cls.record_ticket = cls.record_tickets[0]

        # partners
        cls.partner = cls.env["res.partner"].create(
            {
                "country_id": cls.env.ref("base.be").id,
                "email": "partner@example.com",
                "name": "partner",
                "phone_ids": [
                    Command.create({"number": "0456334455", "type": "landline"})
                ],
            }
        )

        # generate devices and vapid keys to test push impact
        cls._setup_push_devices_for_partners(
            cls.user_admin.partner_id
            + cls.user_employee.partner_id
            + cls.user_follower_emp_email.partner_id
            + cls.user_follower_emp_inbox.partner_id
            + cls.user_follower_portal.partner_id
            + cls.partner_follower
            + cls.user_emp_inbox.partner_id
            + cls.user_emp_email.partner_id
            + cls.partner
            + cls.customers
        )

        # be sure not to be annoyed by ocn / mobile
        cls.env["ir.config_parameter"].sudo().set_param("mail_mobile.enable_ocn", False)


@tagged("mail_performance", "post_install", "-at_install")
class TestPerformance(BaseMailPostPerformance):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tracking_values_ids = [
            (
                0,
                0,
                {
                    "field_id": cls.env["ir.model.fields"]
                    ._get(cls.record_ticket._name, "email_from")
                    .id,
                    "new_value_char": "new_value",
                    "old_value_char": "old_value",
                },
            ),
            (
                0,
                0,
                {
                    "field_id": cls.env["ir.model.fields"]
                    ._get(cls.record_ticket._name, "customer_id")
                    .id,
                    "new_value_char": "New Fake",
                    "new_value_integer": 2,
                    "old_value_char": "Old Fake",
                    "old_value_integer": 1,
                },
            ),
        ]

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_message_post(self):
        """Aims to cover as much features of message_post as possible"""
        followers = (
            self.partner_follower
            + self.user_follower_emp_inbox.partner_id
            + self.user_follower_emp_email.partner_id
        )
        recipients = (
            self.user_emp_inbox.partner_id
            + self.user_emp_email.partner_id
            + self.partner
        )
        ticket = self.record_ticket.with_user(self.env.user)
        ticket.message_subscribe(followers.ids)
        attachments_vals = [  # not linear on number of attachments_vals
            ("attach tuple 1", "attachment tuple content 1"),
            ("attach tuple 2", "attachment tuple content 2", {"cid": "cid1"}),
            ("attach tuple 3", "attachment tuple content 3", {"cid": "cid2"}),
        ]
        attachments = (
            self.env["ir.attachment"]
            .with_user(self.env.user)
            .create(self.test_attachments_vals)
        )
        self.push_to_end_point_mocked.reset_mock()  # reset as executed twice
        self.flush_tracking()

        with self.assertQueryCount(employee=51):
            ticket.message_post(
                attachments=attachments_vals,
                attachment_ids=attachments.ids,
                body=Markup(
                    '<p>Test body <img src="cid:cid1"> <img src="cid:cid2"></p>'
                ),
                email_add_signature=True,
                mail_auto_delete=True,
                message_type="comment",
                parent_id=False,
                partner_ids=recipients.ids,
                subject="Test Subject",
                subtype_xmlid="mail.mt_comment",
                tracking_value_ids=self.tracking_values_ids,
            )
        new_message = ticket.message_ids[0]
        self.assertEqual(
            attachments.mapped("res_model"), [ticket._name for i in range(3)]
        )
        self.assertEqual(attachments.mapped("res_id"), [ticket.id for i in range(3)])
        self.assertTrue(
            new_message.body.startswith('<p>Test body <img src="/web/image/')
        )
        self.assertEqual(new_message.notified_partner_ids, recipients + followers)
        self.assertEqual(
            self.push_to_end_point_mocked.call_count, 6, "Everyone has a device"
        )

    @mute_logger(
        "odoo.tests", "odoo.addons.mail.models.mail_mail", "odoo.models.unlink"
    )
    @users("employee")
    @warmup
    def test_message_post_loop(self):
        """Simulate a loop posting on several records, to check notably cache
        is used."""
        # aims to cover as much features of message_post as possible
        followers = (
            self.partner_follower
            + self.user_follower_emp_inbox.partner_id
            + self.user_follower_emp_email.partner_id
        )
        recipients = (
            self.user_emp_inbox.partner_id
            + self.user_emp_email.partner_id
            + self.partner
        )
        tickets = self.record_tickets.with_user(self.env.user)
        for ticket in tickets:
            ticket.message_subscribe(followers.ids)
        attachments_vals = [  # not linear on number of attachments_vals
            ("attach tuple 1", "attachment tuple content 1"),
            ("attach tuple 2", "attachment tuple content 2", {"cid": "cid1"}),
            ("attach tuple 3", "attachment tuple content 3", {"cid": "cid2"}),
        ]
        attachments_all = [
            self.env["ir.attachment"]
            .with_user(self.env.user)
            .create(self.test_attachments_vals)
            for _ticket in tickets
        ]
        self.push_to_end_point_mocked.reset_mock()  # reset as executed twice
        self.flush_tracking()

        with self.assertQueryCount(employee=375):
            for ticket, attachments in zip(tickets, attachments_all, strict=True):
                ticket.message_post(
                    attachments=attachments_vals,
                    attachment_ids=attachments.ids,
                    body=Markup(
                        '<p>Test body <img src="cid:cid1"> <img src="cid:cid2"></p>'
                    ),
                    email_add_signature=True,
                    mail_auto_delete=True,
                    message_type="comment",
                    parent_id=False,
                    partner_ids=recipients.ids,
                    subject="Test Subject",
                    subtype_xmlid="mail.mt_comment",
                    tracking_value_ids=self.tracking_values_ids,
                )
        for ticket, attachments in zip(tickets, attachments_all, strict=True):
            new_message = ticket.message_ids[0]
            self.assertEqual(
                attachments.mapped("res_model"), [ticket._name for i in range(3)]
            )
            self.assertEqual(
                attachments.mapped("res_id"), [ticket.id for i in range(3)]
            )
            self.assertTrue(
                new_message.body.startswith('<p>Test body <img src="/web/image/')
            )
            self.assertEqual(new_message.notified_partner_ids, recipients + followers)
        self.assertEqual(
            self.push_to_end_point_mocked.call_count,
            6 * 10,
            "Everyone has a device * record count",
        )

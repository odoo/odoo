# Copyright 2015 Therp BV <https://therp.nl>
# © 2018 Pieter Paulussen <pieter_paulussen@me.com>
# © 2021 Stefan Rijnhart <stefan@opener.amsterdam>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import Form, TransactionCase

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG


class AuditlogCommon(object):
    def test_LogCreation(self):
        """First test, caching some data."""

        self.groups_rule.subscribe()

        auditlog_log = self.env["auditlog.log"]
        group = self.env["res.groups"].create({"name": "testgroup1"})
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "create"),
                    ("res_id", "=", group.id),
                ]
            ).ensure_one()
        )
        group.write({"name": "Testgroup1"})
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "write"),
                    ("res_id", "=", group.id),
                ]
            ).ensure_one()
        )
        group.unlink()
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "unlink"),
                    ("res_id", "=", group.id),
                ]
            ).ensure_one()
        )

    def test_LogCreation2(self):
        """Second test, using cached data of the first one."""

        self.groups_rule.subscribe()

        auditlog_log = self.env["auditlog.log"]
        testgroup2 = self.env["res.groups"].create({"name": "testgroup2"})
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "create"),
                    ("res_id", "=", testgroup2.id),
                ]
            ).ensure_one()
        )

    def test_LogCreation3(self):
        """Third test, two groups, the latter being the parent of the former.
        Then we remove it right after (with (2, X) tuple) to test the creation
        of a 'write' log with a deleted resource (so with no text
        representation).
        """

        self.groups_rule.subscribe()
        auditlog_log = self.env["auditlog.log"]
        testgroup3 = testgroup3 = self.env["res.groups"].create({"name": "testgroup3"})
        testgroup4 = self.env["res.groups"].create(
            {"name": "testgroup4", "implied_ids": [(4, testgroup3.id)]}
        )
        testgroup4.write({"implied_ids": [(2, testgroup3.id)]})
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "create"),
                    ("res_id", "=", testgroup3.id),
                ]
            ).ensure_one()
        )
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "create"),
                    ("res_id", "=", testgroup4.id),
                ]
            ).ensure_one()
        )
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "write"),
                    ("res_id", "=", testgroup4.id),
                ]
            ).ensure_one()
        )

    def test_LogCreation4(self):
        """Fourth test, create several records at once (with create multi
        feature starting from Odoo 12) and check that the same number of logs
        has been generated.
        """

        self.groups_rule.subscribe()

        auditlog_log = self.env["auditlog.log"]
        groups_vals = [
            {"name": "testgroup1"},
            {"name": "testgroup3"},
            {"name": "testgroup2"},
        ]
        groups = self.env["res.groups"].create(groups_vals)
        # Ensure that the recordset returns is in the same order
        # than list of vals
        expected_names = ["testgroup1", "testgroup3", "testgroup2"]
        self.assertEqual(groups.mapped("name"), expected_names)

        logs = auditlog_log.search(
            [
                ("model_id", "=", self.groups_model_id),
                ("method", "=", "create"),
                ("res_id", "in", groups.ids),
            ]
        )
        self.assertEqual(len(logs), len(groups))

    def test_LogCreation5(self):
        """Fifth test, create a record and check that the same number of logs
        has been generated. And then delete it, check that it has created log
        with 0 fields updated.
        """
        self.groups_rule.subscribe()

        auditlog_log = self.env["auditlog.log"]
        testgroup5 = self.env["res.groups"].create({"name": "testgroup5"})
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "create"),
                    ("res_id", "=", testgroup5.id),
                ]
            ).ensure_one()
        )
        testgroup5.unlink()
        log_record = auditlog_log.search(
            [
                ("model_id", "=", self.groups_model_id),
                ("method", "=", "unlink"),
                ("res_id", "=", testgroup5.id),
            ]
        ).ensure_one()
        self.assertTrue(log_record)
        if not self.groups_rule.capture_record:
            self.assertEqual(len(log_record.line_ids), 0)

    def test_LogCreation6(self):
        """Six test, create a record and check that the same number of logs
        has been generated. And then delete it, check that it has created log
        with x fields updated as per rule
        """
        self.groups_rule.subscribe()

        auditlog_log = self.env["auditlog.log"]
        testgroup6 = self.env["res.groups"].create({"name": "testgroup6"})
        self.assertTrue(
            auditlog_log.search(
                [
                    ("model_id", "=", self.groups_model_id),
                    ("method", "=", "create"),
                    ("res_id", "=", testgroup6.id),
                ]
            ).ensure_one()
        )
        testgroup6.unlink()
        log_record = auditlog_log.search(
            [
                ("model_id", "=", self.groups_model_id),
                ("method", "=", "unlink"),
                ("res_id", "=", testgroup6.id),
            ]
        ).ensure_one()
        self.assertTrue(log_record)
        if self.groups_rule.capture_record:
            self.assertTrue(len(log_record.line_ids) > 0)


class TestAuditlogFull(TransactionCase, AuditlogCommon):
    def setUp(self):
        super(TestAuditlogFull, self).setUp()
        self.groups_model_id = self.env.ref("base.model_res_groups").id
        self.groups_rule = self.env["auditlog.rule"].create(
            {
                "name": "testrule for groups",
                "model_id": self.groups_model_id,
                "log_read": True,
                "log_create": True,
                "log_write": True,
                "log_unlink": True,
                "log_type": "full",
            }
        )

    def tearDown(self):
        self.groups_rule.unlink()
        super(TestAuditlogFull, self).tearDown()


class TestAuditlogFast(TransactionCase, AuditlogCommon):
    def setUp(self):
        super(TestAuditlogFast, self).setUp()
        self.groups_model_id = self.env.ref("base.model_res_groups").id
        self.groups_rule = self.env["auditlog.rule"].create(
            {
                "name": "testrule for groups",
                "model_id": self.groups_model_id,
                "log_read": True,
                "log_create": True,
                "log_write": True,
                "log_unlink": True,
                "log_type": "fast",
            }
        )

    def tearDown(self):
        self.groups_rule.unlink()
        super(TestAuditlogFast, self).tearDown()


class TestFieldRemoval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Clear all existing logging lines
        existing_audit_logs = cls.env["auditlog.log"].search([])
        existing_audit_logs.unlink()

        # Create a test model to remove
        cls.test_model = (
            cls.env["ir.model"]
            .sudo()
            .create(
                [{"name": "x_test_model", "model": "x_test.model", "state": "manual"}]
            )
        )

        # Create a test model field to remove
        cls.test_field = (
            cls.env["ir.model.fields"]
            .sudo()
            .create(
                [
                    {
                        "name": "x_test_field",
                        "field_description": "x_Test Field",
                        "model_id": cls.test_model.id,
                        "ttype": "char",
                        "state": "manual",
                    }
                ]
            )
        )
        # Setup auditlog rule
        cls.auditlog_rule = cls.env["auditlog.rule"].create(
            [
                {
                    "name": "test.model",
                    "model_id": cls.test_model.id,
                    "log_type": "fast",
                    "log_read": False,
                    "log_create": True,
                    "log_write": True,
                    "log_unlink": False,
                }
            ]
        )

        cls.auditlog_rule.subscribe()
        # Trigger log creation
        rec = cls.env["x_test.model"].create({"x_test_field": "test value"})
        rec.write({"x_test_field": "test value 2"})

        cls.logs = cls.env["auditlog.log"].search(
            [("res_id", "=", rec.id), ("model_id", "=", cls.test_model.id)]
        )

    def assert_values(self):
        """Assert that the denormalized field and model info is present
        on the auditlog records"""
        self.logs.invalidate_recordset()
        self.assertEqual(self.logs[0].model_name, "x_test_model")
        self.assertEqual(self.logs[0].model_model, "x_test.model")

        log_lines = self.logs.mapped("line_ids")
        self.assertEqual(len(log_lines), 2)
        self.assertEqual(log_lines[0].field_name, "x_test_field")
        self.assertEqual(log_lines[0].field_description, "x_Test Field")

        self.auditlog_rule.invalidate_recordset()
        self.assertEqual(self.auditlog_rule.model_name, "x_test_model")
        self.assertEqual(self.auditlog_rule.model_model, "x_test.model")

    def test_01_field_and_model_removal(self):
        """Test field and model removal to check auditlog line persistence"""
        self.assert_values()

        # Remove the field
        self.test_field.with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()
        self.assert_values()
        # The field should not be linked
        self.assertFalse(self.logs.mapped("line_ids.field_id"))

        # Remove the model
        self.test_model.with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()
        self.assert_values()

        # The model should not be linked
        self.assertFalse(self.logs.mapped("model_id"))
        # Assert rule values
        self.assertFalse(self.auditlog_rule.model_id)


class TestAuditlogFullCaptureRecord(TransactionCase, AuditlogCommon):
    def setUp(self):
        super(TestAuditlogFullCaptureRecord, self).setUp()
        self.groups_model_id = self.env.ref("base.model_res_groups").id
        self.groups_rule = self.env["auditlog.rule"].create(
            {
                "name": "testrule for groups with capture unlink record",
                "model_id": self.groups_model_id,
                "log_read": True,
                "log_create": True,
                "log_write": True,
                "log_unlink": True,
                "log_type": "full",
                "capture_record": True,
            }
        )

    def tearDown(self):
        self.groups_rule.unlink()
        super(TestAuditlogFullCaptureRecord, self).tearDown()


class AuditLogRuleTestForUserFields(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(AuditLogRuleTestForUserFields, cls).setUpClass()
        # get Contact model id
        cls.contact_model_id = (
            cls.env["ir.model"].search([("model", "=", "res.partner")]).id
        )

        # get phone field id
        cls.fields_to_exclude_ids = (
            cls.env["ir.model.fields"]
            .search([("model", "=", "res.partner"), ("name", "=", "phone")])
            .id
        )

        # get user id
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": "Test User",
                    "login": "testuser",
                }
            )
        )
        cls.user_2 = (
            cls.env["res.users"]
            .with_context(no_reset_password=True, tracking_disable=True)
            .create(
                {
                    "name": "Test User2",
                    "login": "testuser2",
                }
            )
        )

        cls.users_to_exclude_ids = cls.user.id

        # creating auditlog.rule
        cls.auditlog_rule = (
            cls.env["auditlog.rule"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "testrule 01",
                    "model_id": cls.contact_model_id,
                    "log_read": True,
                    "log_create": True,
                    "log_write": True,
                    "log_unlink": True,
                    "log_type": "full",
                    "capture_record": True,
                }
            )
        )

        # Updating phone in fields_to_exclude_ids
        cls.auditlog_rule.fields_to_exclude_ids = [[4, cls.fields_to_exclude_ids]]

        # Updating users_to_exclude_ids
        cls.auditlog_rule.users_to_exclude_ids = [[4, cls.users_to_exclude_ids]]

        # Subscribe auditlog.rule
        cls.auditlog_rule.subscribe()

        cls.auditlog_log = cls.env["auditlog.log"]

        # Creating new res.partner
        cls.testpartner1 = (
            cls.env["res.partner"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "testpartner1",
                    "phone": "123",
                }
            )
        )

        # Creating new res.partner from excluded user
        cls.testpartner2 = (
            cls.env["res.partner"]
            .with_context(tracking_disable=True)
            .with_user(cls.user.id)
            .create(
                {
                    "name": "testpartner2",
                }
            )
        )

    def test_01_AuditlogFull_field_exclude_create_log(self):
        # Checking log is created for testpartner1
        create_log_record = self.auditlog_log.search(
            [
                ("model_id", "=", self.auditlog_rule.model_id.id),
                ("method", "=", "create"),
                ("res_id", "=", self.testpartner1.id),
            ]
        ).ensure_one()
        self.assertTrue(create_log_record)
        field_names = create_log_record.line_ids.mapped("field_name")

        # Checking log lines not created for phone
        self.assertTrue("phone" not in field_names)

        # Removing created log record
        create_log_record.unlink()

    def test_02_AuditlogFull_field_exclude_write_log(self):
        # Checking fields_to_exclude_ids
        self.testpartner1.with_context(tracking_disable=True).write(
            {
                "phone": "1234567890",
            }
        )
        # Checking log is created for testpartner1
        write_log_record = self.auditlog_log.search(
            [
                ("model_id", "=", self.auditlog_rule.model_id.id),
                ("method", "=", "write"),
                ("res_id", "=", self.testpartner1.id),
            ]
        ).ensure_one()
        self.assertTrue(write_log_record)
        field_names = write_log_record.line_ids.mapped("field_name")

        # Checking log lines not created for phone
        self.assertTrue("phone" not in field_names)

    def test_03_AuditlogFull_user_exclude_write_log(self):
        # Update email in Form view with excluded user
        partner_form = Form(
            self.testpartner1.with_user(self.user.id).with_context(
                tracking_disable=True
            )
        )
        partner_form.email = "vendor@mail.com"
        testpartner1 = partner_form.save()

        # Checking write log not created
        with self.assertRaises(ValueError):
            self.auditlog_log.search(
                [
                    ("model_id", "=", self.auditlog_rule.model_id.id),
                    ("method", "=", "write"),
                    ("res_id", "=", testpartner1.id),
                    ("user_id", "=", self.user.id),
                ]
            ).ensure_one()

    def test_04_AuditlogFull_user_exclude_create_log(self):
        # Checking create log not created for testpartner2
        with self.assertRaises(ValueError):
            self.auditlog_log.search(
                [
                    ("model_id", "=", self.auditlog_rule.model_id.id),
                    ("method", "=", "create"),
                    ("res_id", "=", self.testpartner2.id),
                ]
            ).ensure_one()

    def test_05_AuditlogFull_user_exclude_unlink_log(self):
        # Removing testpartner2 from excluded user
        self.testpartner2.with_user(self.user).unlink()

        # Checking delete log not created for testpartner2
        with self.assertRaises(ValueError):
            self.auditlog_log.search(
                [
                    ("model_id", "=", self.auditlog_rule.model_id.id),
                    ("method", "=", "unlink"),
                    ("res_id", "=", self.testpartner2.id),
                ]
            ).ensure_one()

    def test_06_AuditlogFull_unlink_log(self):
        # Removing testpartner1 with user_2
        self.testpartner1.with_user(self.user_2).unlink()
        delete_log_record = self.auditlog_log.search(
            [
                ("model_id", "=", self.auditlog_rule.model_id.id),
                ("method", "=", "unlink"),
                ("res_id", "=", self.testpartner1.id),
                ("user_id", "=", self.user_2.id),
            ]
        ).ensure_one()

        # Checking log lines are created
        self.assertTrue(delete_log_record)

        # Removing auditlog_rule
        self.auditlog_rule.unlink()

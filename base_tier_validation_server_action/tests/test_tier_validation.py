# Copyright 2020 Ecosoft (http://ecosoft.co.th)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo_test_helper import FakeModelLoader

from odoo.tests import common
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TierTierValidation(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TierTierValidation, cls).setUpClass()

        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .tier_validation_tester import TierValidationTester

        cls.loader.update_registry((TierValidationTester,))
        cls.test_model = cls.env[TierValidationTester._name]
        cls.tester_model = cls.env["ir.model"].search(
            [("model", "=", "tier.validation.tester")]
        )

        # Access record:
        cls.env["ir.model.access"].create(
            {
                "name": "access.tester",
                "model_id": cls.tester_model.id,
                "perm_read": 1,
                "perm_write": 1,
                "perm_create": 1,
                "perm_unlink": 1,
            }
        )

        # Create users:
        cls.group_system = cls.env.ref("base.group_system")
        group_ids = cls.group_system.ids
        cls.test_user_1 = cls.env["res.users"].create(
            {"name": "John", "login": "test1", "groups_id": [(6, 0, group_ids)]}
        )
        cls.test_user_2 = cls.env["res.users"].create(
            {"name": "Mike", "login": "test2"}
        )
        cls.test_user_3 = cls.env["res.users"].create(
            {"name": "John Wick", "login": "test3", "groups_id": [(6, 0, group_ids)]}
        )

        # Create tier definitions:
        cls.tier_def_obj = cls.env["tier.definition"]
        cls.tier_def_obj.create(
            {
                "model_id": cls.tester_model.id,
                "review_type": "individual",
                "reviewer_id": cls.test_user_1.id,
                "definition_domain": "[('test_field', '>', 1.0)]",
                "sequence": 30,
            }
        )

        cls.test_record = cls.test_model.create({"test_field": 2.5})

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_1_auto_validation(self):
        # Create new test record
        test_record = self.test_model.create({"test_field": 2.5})
        # Create tier definitions
        self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_id": self.test_user_1.id,
                "sequence": 20,
                "approve_sequence": True,
                "auto_validate": True,
            }
        )
        self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_id": self.test_user_1.id,
                "sequence": 10,
                "approve_sequence": True,
                "auto_validate": True,
                "auto_validate_domain": "[('test_field', '>', 3)]",
            }
        )
        # Request validation
        test_record.with_user(self.test_user_2).request_validation()
        record = test_record.with_user(self.test_user_1)
        record.invalidate_recordset()
        # Auto validate, 1st tier, not auto validated
        self.tier_def_obj._cron_auto_tier_validation()
        self.assertEqual(
            record.review_ids.mapped("status"), ["pending", "pending", "pending"]
        )
        # Manual validate 2nd tier -> OK
        record.validate_tier()
        self.assertEqual(
            record.review_ids.mapped("status"), ["approved", "pending", "pending"]
        )
        # Auto validate, 2nd tier -> OK
        self.tier_def_obj._cron_auto_tier_validation()
        self.assertEqual(
            record.review_ids.mapped("status"), ["approved", "approved", "pending"]
        )
        # Auto validate, 3rd tier -> Not pass validate domain
        self.tier_def_obj._cron_auto_tier_validation()
        self.assertEqual(
            record.review_ids.mapped("status"), ["approved", "approved", "pending"]
        )
        # Manual validate 3rd tier -> OK
        record.validate_tier()
        self.assertEqual(
            record.review_ids.mapped("status"), ["approved", "approved", "approved"]
        )

    def test_2_auto_validation_exception(self):
        # Create new test record
        test_record = self.test_model.create({"test_field": 2.5})
        # Create tier definitions
        self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_group_id": self.group_system.id,
                "sequence": 20,
                "approve_sequence": True,
                "auto_validate": True,
            }
        )
        # Request validation
        test_record.with_user(self.test_user_2).request_validation()
        record = test_record.with_user(self.test_user_1)
        record.invalidate_recordset()
        # Auto validate, 1st tier, not auto validated
        self.tier_def_obj._cron_auto_tier_validation()
        self.assertEqual(record.review_ids.mapped("status"), ["pending", "pending"])
        # Manual validate 2nd tier -> OK
        record.validate_tier()
        self.assertEqual(record.review_ids.mapped("status"), ["approved", "pending"])
        # Auto validate, 2nd tier -> Not OK, before len(reviewers) > 1
        self.tier_def_obj._cron_auto_tier_validation()
        self.assertEqual(record.review_ids.mapped("status"), ["approved", "pending"])

    def test_3_trigger_server_action(self):
        # Create new test record
        test_record = self.test_model.create({"test_field": 2.5})
        # Create server action
        server_action = self.env["ir.actions.server"].create(
            {
                "name": "Set test_bool = True",
                "model_id": self.tester_model.id,
                "state": "code",
                "code": "record.write({'test_bool': True})",
            }
        )
        # Create tier definitions
        self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_id": self.test_user_1.id,
                "sequence": 20,
                "server_action_id": server_action.id,  # Server Action
            }
        )
        # Request validation
        test_record.with_user(self.test_user_2).request_validation()
        record = test_record.with_user(self.test_user_1)
        record.invalidate_recordset()
        record.validate_tier()
        self.assertTrue(record.test_bool)

    def test_4_trigger_rejected_server_action(self):
        # Create new test record
        test_record = self.test_model.create({"test_field": 2.5})
        # Create rejected server action
        rejected_server_action = self.env["ir.actions.server"].create(
            {
                "name": "Set test_bool = True",
                "model_id": self.tester_model.id,
                "state": "code",
                "code": "record.write({'test_bool': True})",
            }
        )
        # Create tier definitions
        self.tier_def_obj.create(
            {
                "model_id": self.tester_model.id,
                "review_type": "individual",
                "reviewer_id": self.test_user_1.id,
                "sequence": 20,
                "rejected_server_action_id": rejected_server_action.id,
            }
        )
        # Request rejection
        test_record.with_user(self.test_user_2).request_validation()
        record = test_record.with_user(self.test_user_1)
        record.invalidate_recordset()
        record.reject_tier()
        self.assertTrue(record.test_bool)

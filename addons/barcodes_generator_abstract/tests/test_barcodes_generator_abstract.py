# Copyright 2021 Tecnativa - Carlos Roca
# Copyright 2023-Today GRAP (http://www.grap.coop)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo_test_helper import FakeModelLoader

from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestBarcodesGeneratorAbstract(TransactionCase, FakeModelLoader):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .models import BarcodeGeneratorUserFake, BarcodeRuleUserFake

        cls.loader.update_registry(
            (
                BarcodeGeneratorUserFake,
                BarcodeRuleUserFake,
            )
        )
        cls.barcode_rule_fake = cls.env["barcode.rule"].create(
            {
                "name": "User rule",
                "barcode_nomenclature_id": cls.env.ref(
                    "barcodes.default_barcode_nomenclature"
                ).id,
                "type": "user",
                "sequence": 999,
                "encoding": "ean13",
                "pattern": "20.....{NNNDD}",
                "generate_type": "manual",
                "generate_model": "res.users",
            }
        )
        cls.user_fake = cls.env["res.users"].create(
            {
                "name": "Test user",
                "login": "testing_01",
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_generate_sequence_manually(self):
        self.user_fake.barcode_rule_id = self.barcode_rule_fake
        self.assertFalse(self.user_fake.barcode_base)
        self.assertFalse(self.user_fake.barcode)

        with self.assertRaises(UserError):
            self.user_fake.generate_base()

        self.user_fake.generate_barcode()
        self.assertEqual(
            self.user_fake.barcode,
            "2000000000008",
        )
        self.user_fake.barcode_base = 10
        self.user_fake.generate_barcode()
        self.assertEqual(
            self.user_fake.barcode,
            "2000010000005",
        )

    def test_generate_sequence_sequence(self):
        self.barcode_rule_fake.generate_type = "sequence"
        self.assertTrue(self.barcode_rule_fake.sequence_id)

        self.user_fake.barcode_rule_id = self.barcode_rule_fake
        self.assertFalse(self.user_fake.barcode_base)
        self.assertFalse(self.user_fake.barcode)

        self.user_fake.generate_base()
        self.assertEqual(self.user_fake.barcode_base, 1)
        self.assertFalse(self.user_fake.barcode)

        self.user_fake.generate_barcode()
        self.assertEqual(self.user_fake.barcode, "2000001000007")

        self.user_fake.barcode_base = False
        self.user_fake.generate_base()
        self.assertEqual(self.user_fake.barcode_base, 2)
        self.user_fake.generate_barcode()
        self.assertEqual(self.user_fake.barcode, "2000002000006")

    def test_generate_sequence_sequence_automate(self):
        self.barcode_rule_fake.write(
            {
                "generate_type": "sequence",
                "generate_automate": True,
            }
        )
        self.assertTrue(self.barcode_rule_fake.sequence_id)

        self.user_fake.barcode_rule_id = self.barcode_rule_fake
        self.assertEqual(self.user_fake.barcode_base, 1)
        self.assertEqual(self.user_fake.barcode, "2000001000007")

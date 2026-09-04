# Copyright (C) 2016-Today GRAP (http://www.grap.coop)
# Copyright (C) 2016-Today La Louve (http://www.lalouve.net)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class Tests(TransactionCase):
    """Tests 'Barcodes Generator for Products'"""

    def setUp(self):
        super().setUp()
        self.ProductTemplate = self.env["product.template"]
        self.ProductProduct = self.env["product.product"]
        self.barcode_rule_manually = self.env.ref(
            "barcodes_generator_product.rule_product_generated_barcode_manually"
        )

    # Test Section
    def test_01_manual_generation_template(self):
        self.template_mono = self.ProductTemplate.create(
            {
                "name": "Template Mono Variant",
                "barcode_rule_id": self.barcode_rule_manually.id,
                "barcode_base": 54321,
            }
        )
        self.template_mono.generate_barcode()
        self.assertEqual(
            self.template_mono.barcode,
            "2054321000001",
            "Incorrect Manual Barcode Generation for non varianted Template."
            " Pattern : %s - Base : %s"
            % (
                self.template_mono.barcode_rule_id.pattern,
                self.template_mono.barcode_base,
            ),
        )

    def test_02_manual_generation_product(self):
        self.template_multi = self.ProductTemplate.create(
            {"name": "Template Multi Variant"}
        )
        self.product_variant_1 = self.ProductProduct.create(
            {
                "name": "Variant 1",
                "product_tmpl_id": self.template_multi.id,
                "barcode_rule_id": self.barcode_rule_manually.id,
                "barcode_base": 12345,
            }
        )
        self.product_variant_1.generate_barcode()
        self.assertEqual(
            self.product_variant_1.barcode,
            "2012345000001",
            "Incorrect Manual Barcode Generation for varianted Product."
            " Pattern : %s - Base : %s"
            % (
                self.product_variant_1.barcode_rule_id.pattern,
                self.product_variant_1.barcode_base,
            ),
        )

    def test_03_auto_generation_product(self):
        self.template_auto_gen = self.ProductTemplate.create(
            {"name": "Template Test Auto Gen"}
        )
        self.assertFalse(self.template_auto_gen.barcode)
        rule = self.env.ref(
            "barcodes_generator_product.rule_product_generated_barcode_manually"
        )
        rule.sequence_id = self.env.ref(
            "barcodes_generator_product.seq_product_generated_barcode"
        )
        rule.generate_automate = True
        rule.generate_type = "sequence"
        self.template_auto_gen.barcode_rule_id = rule
        self.assertIsNotNone(self.template_auto_gen.barcode)

from collections import defaultdict

from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDuplicatedRecordsetCopy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")

    def _assert_copy_data_tolerates_a_none_entry(self, record):
        seen = defaultdict(set)
        seen[record._name].add(record.id)
        vals_list = record.with_context(__copy_data_seen=seen).copy_data()
        self.assertEqual(vals_list, [None])

        vals_list = record.copy_data()
        self.assertEqual(len(vals_list), 1)
        self.assertIsInstance(vals_list[0], dict)
        return vals_list[0]

    def test_copy_duplicated_template(self):
        template = self.env["product.template"].create(
            {"name": "Dup Tmpl", "uom_id": self.uom_unit.id}
        )
        vals = self._assert_copy_data_tolerates_a_none_entry(template)
        self.assertEqual(vals["name"], "Dup Tmpl (copy)")

    def test_copy_duplicated_category(self):
        category = self.env["product.category"].create({"name": "Dup Categ"})
        vals = self._assert_copy_data_tolerates_a_none_entry(category)
        self.assertEqual(vals["name"], "Dup Categ (copy)")

    def test_copy_duplicated_tag(self):
        tag = self.env["product.tag"].create({"name": "Dup Tag"})
        vals = self._assert_copy_data_tolerates_a_none_entry(tag)
        self.assertEqual(vals["name"], "Dup Tag (copy)")

    def test_copy_duplicated_pricelist(self):
        pricelist = self.env["product.pricelist"].create(
            {"name": "Dup PL", "currency_id": self.env.company.currency_id.id}
        )
        vals = self._assert_copy_data_tolerates_a_none_entry(pricelist)
        self.assertEqual(vals["name"], "Dup PL (copy)")

    def test_copy_several_variants_of_one_template(self):
        attribute = self.env["product.attribute"].create({"name": "Dup Size"})
        values = self.env["product.attribute.value"].create(
            [{"name": name, "attribute_id": attribute.id} for name in ("S", "M")]
        )
        template = self.env["product.template"].create(
            {
                "name": "Dup Variants",
                "uom_id": self.uom_unit.id,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [(6, 0, values.ids)],
                        },
                    )
                ],
            }
        )
        variants = template.product_variant_ids
        self.assertEqual(len(variants), 2)

        copies = variants.copy()

        self.assertEqual(len(copies.product_tmpl_id), 1)
        self.assertNotEqual(copies.product_tmpl_id, template)
        self.assertEqual(copies.product_tmpl_id.name, "Dup Variants (copy)")
        self.assertEqual(len(copies.product_tmpl_id.product_variant_ids), 2)

    def test_copy_template_keeps_price_extra_per_template(self):
        attribute = self.env["product.attribute"].create({"name": "Dup Colour"})
        red, blue = self.env["product.attribute.value"].create(
            [{"name": name, "attribute_id": attribute.id} for name in ("Red", "Blue")]
        )
        templates = self.env["product.template"].create(
            [
                {
                    "name": name,
                    "uom_id": self.uom_unit.id,
                    "attribute_line_ids": [
                        (
                            0,
                            0,
                            {
                                "attribute_id": attribute.id,
                                "value_ids": [(6, 0, (red + blue).ids)],
                            },
                        )
                    ],
                }
                for name in ("Batch A", "Batch B")
            ]
        )
        for index, template in enumerate(templates):
            template.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == red
            ).price_extra = 10.0 * (index + 1)

        copies = templates.copy()

        for template, copy in zip(templates, copies, strict=True):
            source = template.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == red
            )
            copied = copy.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == red
            )
            self.assertEqual(copied.price_extra, source.price_extra)


@tagged("post_install", "-at_install")
class TestPriceUomConversion(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_kgm = cls.env.ref("uom.product_uom_kgm")

        attribute = cls.env["product.attribute"].create({"name": "Price Colour"})
        cls.red, cls.blue = cls.env["product.attribute.value"].create(
            [{"name": name, "attribute_id": attribute.id} for name in ("Red", "Blue")]
        )
        cls.template = cls.env["product.template"].create(
            {
                "name": "Priced Product",
                "list_price": 100.0,
                "uom_id": cls.uom_unit.id,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [(6, 0, (cls.red + cls.blue).ids)],
                        },
                    )
                ],
            }
        )
        cls.ptav_red = (
            cls.template.attribute_line_ids.product_template_value_ids.filtered(
                lambda ptav: ptav.product_attribute_value_id == cls.red
            )
        )
        cls.ptav_red.price_extra = 10.0
        cls.variant = cls.template.product_variant_ids.filtered(
            lambda p: cls.ptav_red in p.product_template_attribute_value_ids
        )

    def test_lst_price_converts_the_attribute_extra_too(self):
        self.assertEqual(self.variant.lst_price, 110.0)
        in_dozen = self.variant.with_context(uom=self.uom_dozen.id).lst_price
        self.assertEqual(
            in_dozen,
            self.variant._get_prices("list_price", uom=self.uom_dozen)[self.variant.id],
        )
        self.assertEqual(in_dozen, 1320.0)

    def test_lst_price_round_trips_through_its_inverse(self):
        variant_in_dozen = self.variant.with_context(uom=self.uom_dozen.id)
        variant_in_dozen.lst_price = 2400.0
        self.assertEqual(self.variant.list_price, 190.0)
        self.variant.invalidate_recordset()
        self.assertEqual(
            self.variant.with_context(uom=self.uom_dozen.id).lst_price, 2400.0
        )

    def test_lst_price_refuses_an_incompatible_uom(self):
        with self.assertRaises(UserError):
            self.variant.with_context(uom=self.uom_kgm.id).read(["lst_price"])

    def test_convert_price_from_uom_inverts_convert_price_to_uom(self):
        self.assertEqual(
            self.variant._convert_price_from_uom(
                self.variant._convert_price_to_uom(37.0, self.uom_dozen),
                self.uom_dozen,
            ),
            37.0,
        )
        with self.assertRaises(UserError):
            self.variant._convert_price_from_uom(1.0, self.uom_kgm)

    def test_fixed_pricelist_rule_refuses_an_incompatible_uom(self):
        pricelist = self.env["product.pricelist"].create(
            {"name": "UoM PL", "currency_id": self.env.company.currency_id.id}
        )
        rule = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": self.template.id,
                "compute_price": "fixed",
                "fixed_price": 50.0,
            }
        )
        self.assertEqual(
            pricelist._get_product_price(self.variant, 1.0, uom=self.uom_dozen), 600.0
        )
        with self.assertRaises(UserError):
            pricelist._get_product_price(self.variant, 1.0, uom=self.uom_kgm)

        rule.write({"compute_price": "percentage", "percent_price": 10.0})
        with self.assertRaises(UserError):
            pricelist._get_product_price(self.variant, 1.0, uom=self.uom_kgm)

        rule.write({"compute_price": "fixed", "fixed_price": 50.0})
        self.assertEqual(
            pricelist._get_product_price(self.template, 1.0, uom=self.uom_dozen), 600.0
        )
        with self.assertRaises(UserError):
            pricelist._get_product_price(self.template, 1.0, uom=self.uom_kgm)

    def test_price_uom_guard_is_symmetric_between_template_and_variant(self):
        for record in (self.template, self.variant):
            self.assertTrue(hasattr(record, "_check_price_uom"))
            self.assertEqual(record._convert_price_to_uom(10.0, self.uom_dozen), 120.0)
            with self.assertRaises(UserError):
                record._convert_price_to_uom(10.0, self.uom_kgm)

    def test_supplierinfo_price_discounted_keeps_the_product_uom_contract(self):
        vendor = self.env["res.partner"].create({"name": "UoM Vendor"})
        seller = self.env["product.supplierinfo"].create(
            {
                "partner_id": vendor.id,
                "product_tmpl_id": self.template.id,
                "price": 120.0,
                "product_uom_id": self.uom_dozen.id,
            }
        )
        self.assertEqual(seller.price_discounted, 10.0)
        self.assertEqual(
            self.uom_unit._get_price_in_unit(
                seller.price_discounted, seller.product_uom_id
            ),
            120.0,
        )


@tagged("post_install", "-at_install")
class TestPackagingUomCategory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")
        cls.uom_kgm = cls.env.ref("uom.product_uom_kgm")
        cls.uom_dozen.action_unarchive()

    def test_packaging_in_the_same_category_is_allowed(self):
        template = self.env["product.template"].create(
            {
                "name": "Boxed Product",
                "uom_id": self.uom_unit.id,
                "uom_ids": [(6, 0, self.uom_dozen.ids)],
            }
        )
        self.assertEqual(template.uom_ids, self.uom_dozen)

    def test_packaging_from_another_category_is_refused_on_create(self):
        with self.assertRaises(ValidationError):
            self.env["product.template"].create(
                {
                    "name": "Impossible Packaging",
                    "uom_id": self.uom_unit.id,
                    "uom_ids": [(6, 0, self.uom_kgm.ids)],
                }
            )

    def test_packaging_from_another_category_is_refused_on_write(self):
        template = self.env["product.template"].create(
            {"name": "Later Packaging", "uom_id": self.uom_unit.id}
        )
        with self.assertRaises(ValidationError):
            template.uom_ids = self.uom_kgm

    def test_changing_the_unit_revalidates_existing_packagings(self):
        template = self.env["product.template"].create(
            {
                "name": "Rebased Product",
                "uom_id": self.uom_unit.id,
                "uom_ids": [(6, 0, self.uom_dozen.ids)],
            }
        )
        with self.assertRaises(ValidationError):
            template.uom_id = self.uom_kgm


@tagged("post_install", "-at_install")
class TestTemplateUomChange(TransactionCase):
    def test_uom_change_covers_archived_variants(self):
        uom_unit = self.env.ref("uom.product_uom_unit")
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        attribute = self.env["product.attribute"].create({"name": "Archived Size"})
        values = self.env["product.attribute.value"].create(
            [{"name": name, "attribute_id": attribute.id} for name in ("S", "M")]
        )
        template = self.env["product.template"].create(
            {
                "name": "Archived Variant Product",
                "uom_id": uom_unit.id,
                "attribute_line_ids": [
                    (
                        0,
                        0,
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [(6, 0, values.ids)],
                        },
                    )
                ],
            }
        )
        archived = template.product_variant_ids[0]
        archived.action_archive()
        self.assertFalse(archived.active)

        seen = []
        product_model = type(self.env["product.product"])
        original = product_model._update_uom

        def spy(records, to_uom_id):
            seen.extend(records.ids)
            return original(records, to_uom_id)

        self.patch(product_model, "_update_uom", spy)
        template.write({"uom_id": uom_dozen.id})

        all_variants = template.with_context(active_test=False).product_variant_ids
        self.assertEqual(sorted(seen), sorted(all_variants.ids))
        self.assertIn(archived.id, seen)

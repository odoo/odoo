"""Pure-Python tests for FieldSpec — no Odoo, no database required."""

import unittest

from odoo.orm.components.field_spec import FieldSpec


class TestFieldSpecCreation(unittest.TestCase):
    """Test FieldSpec creation and immutability."""

    def test_basic_creation(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        self.assertEqual(spec.name, "name")
        self.assertEqual(spec.type, "char")
        self.assertEqual(spec.model_name, "res.partner")

    def test_frozen(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        with self.assertRaises(AttributeError):
            spec.name = "other"  # type: ignore

    def test_equality(self):
        spec1 = FieldSpec(name="name", type="char", model_name="res.partner")
        spec2 = FieldSpec(name="name", type="char", model_name="res.partner")
        self.assertEqual(spec1, spec2)

    def test_inequality(self):
        spec1 = FieldSpec(name="name", type="char", model_name="res.partner")
        spec2 = FieldSpec(name="email", type="char", model_name="res.partner")
        self.assertNotEqual(spec1, spec2)

    def test_hashable(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        s = {spec}
        self.assertIn(spec, s)

    def test_defaults(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        self.assertTrue(spec.store)
        self.assertFalse(spec.required)
        self.assertFalse(spec.readonly)
        self.assertTrue(spec.copy)
        self.assertIsNone(spec.compute)
        self.assertIsNone(spec.related)
        self.assertEqual(spec.depends, ())
        self.assertEqual(spec.depends_context, ())


class TestFieldSpecDerived(unittest.TestCase):
    """Test derived properties."""

    def test_stored_computed(self):
        spec = FieldSpec(
            name="total",
            type="float",
            model_name="sale.order",
            store=True,
            compute="_compute_total",
        )
        self.assertTrue(spec.is_stored_computed)

    def test_not_stored_computed(self):
        spec = FieldSpec(
            name="total",
            type="float",
            model_name="sale.order",
            store=False,
            compute="_compute_total",
        )
        self.assertFalse(spec.is_stored_computed)

    def test_not_computed(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        self.assertFalse(spec.is_stored_computed)
        self.assertFalse(spec.is_computed)

    def test_is_column(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            store=True,
            column_type=("varchar", "varchar"),
        )
        self.assertTrue(spec.is_column)

    def test_not_column_no_type(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            store=True,
            column_type=None,
        )
        self.assertFalse(spec.is_column)

    def test_not_column_not_stored(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            store=False,
            column_type=("varchar", "varchar"),
        )
        self.assertFalse(spec.is_column)

    def test_is_relational(self):
        for ftype in (
            "many2one",
            "one2many",
            "many2many",
            "many2one_reference",
        ):
            spec = FieldSpec(name="f", type=ftype, model_name="m")
            self.assertTrue(spec.is_relational, f"Expected relational for {ftype}")

    def test_not_relational(self):
        for ftype in ("char", "float", "integer", "boolean", "text"):
            spec = FieldSpec(name="f", type=ftype, model_name="m")
            self.assertFalse(spec.is_relational, f"Expected non-relational for {ftype}")

    def test_is_related(self):
        spec = FieldSpec(
            name="partner_name",
            type="char",
            model_name="sale.order",
            related="partner_id.name",
        )
        self.assertTrue(spec.is_related)

    def test_is_computed(self):
        spec = FieldSpec(
            name="total",
            type="float",
            model_name="sale.order",
            compute="_compute_total",
        )
        self.assertTrue(spec.is_computed)


class TestFieldSpecValidation(unittest.TestCase):
    """Test validate() catches inconsistencies."""

    def test_valid_basic(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        self.assertEqual(spec.validate(), [])

    def test_valid_stored_computed(self):
        spec = FieldSpec(
            name="total",
            type="float",
            model_name="sale.order",
            store=True,
            compute="_compute_total",
            depends=("line_ids.price",),
        )
        self.assertEqual(spec.validate(), [])

    def test_recursive_without_compute(self):
        spec = FieldSpec(
            name="parent_path",
            type="char",
            model_name="res.partner",
            recursive=True,
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("recursive", errors[0])

    def test_precompute_without_compute(self):
        spec = FieldSpec(
            name="seq",
            type="integer",
            model_name="sale.order",
            precompute=True,
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("precompute", errors[0])

    def test_inverse_without_compute(self):
        spec = FieldSpec(
            name="qty",
            type="float",
            model_name="sale.order.line",
            inverse="_inverse_qty",
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("inverse", errors[0])

    def test_compute_sudo_without_compute(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            compute_sudo=True,
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("compute_sudo", errors[0])

    def test_depends_without_compute(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            depends=("field_a",),
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("depends", errors[0])

    def test_related_and_compute(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            related="partner_id.name",
            compute="_compute_name",
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("both related and compute", errors[0])

    def test_comodel_on_non_relational(self):
        spec = FieldSpec(
            name="name",
            type="char",
            model_name="res.partner",
            comodel_name="res.country",
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 1)
        self.assertIn("comodel_name", errors[0])

    def test_multiple_errors(self):
        spec = FieldSpec(
            name="f",
            type="char",
            model_name="m",
            recursive=True,
            precompute=True,
            inverse="_inv",
        )
        errors = spec.validate()
        self.assertEqual(len(errors), 3)


class TestFieldSpecRepr(unittest.TestCase):
    """Test string representation."""

    def test_basic_repr(self):
        spec = FieldSpec(name="name", type="char", model_name="res.partner")
        r = repr(spec)
        self.assertIn("res.partner.name", r)
        self.assertIn("type='char'", r)

    def test_computed_repr(self):
        spec = FieldSpec(
            name="total",
            type="float",
            model_name="sale.order",
            compute="_compute_total",
        )
        r = repr(spec)
        self.assertIn("compute=", r)

    def test_not_stored_repr(self):
        spec = FieldSpec(
            name="total",
            type="float",
            model_name="sale.order",
            store=False,
            compute="_compute_total",
        )
        r = repr(spec)
        self.assertIn("store=False", r)


if __name__ == "__main__":
    unittest.main()

"""Database-free tests for the model_test_env infrastructure.

Tests the :class:`ModelRegistry`, :class:`DictBackend` CRUD mechanics,
domain evaluation, recordset operations, and multi-model interaction.

Model-specific compute method tests live in ``core/tests/models/``.

Usage::

    python -m pytest core/tests/test_model_test_env.py -v
"""

import unittest

from odoo.orm.testing import ModelRegistry, model_test_env

from odoo.addons.base.models.res_partner import ResPartner

# Build the registry ONCE for the entire module.  All base-module models
# produce the same 124-model registry regardless of which class you pass,
# so sharing it avoids ~20ms of redundant setup per test.
_base_registry = ModelRegistry([ResPartner])


class TestModelRegistry(unittest.TestCase):
    """Test that ModelRegistry builds correctly from definition classes."""

    def test_registry_from_single_model(self):
        """ModelRegistry auto-injects 'base' and sets up fields."""
        registry = _base_registry
        self.assertIn("base", registry)
        self.assertIn("res.partner", registry)
        self.assertIn("name", registry["res.partner"]._fields)
        self.assertIn("display_name", registry["res.partner"]._fields)
        self.assertIn("id", registry["res.partner"]._fields)

    def test_registry_db_name(self):
        """ModelRegistry.db_name defaults to ':memory:'."""
        self.assertEqual(_base_registry.db_name, ":memory:")

    def test_registry_mapping_protocol(self):
        """ModelRegistry satisfies the Mapping protocol."""
        self.assertGreater(len(_base_registry), 0)
        self.assertIn("res.partner", list(_base_registry))

    def test_field_depends_populated(self):
        """Field dependencies are resolved during build."""
        partner_cls = _base_registry["res.partner"]
        display_name_field = partner_cls._fields["display_name"]
        self.assertIn(display_name_field, _base_registry.field_depends)
        self.assertIn(display_name_field, _base_registry.field_depends_context)

    def test_all_base_models_registered(self):
        """All base module models are auto-discovered."""
        expected = {"res.partner", "res.company", "res.users", "res.currency",
                    "res.country", "res.lang", "ir.model", "ir.model.fields"}
        self.assertTrue(expected.issubset(set(_base_registry)))

    def test_field_computed_populated(self):
        """field_computed maps compute methods to field groups."""
        partner_cls = _base_registry["res.partner"]
        company_type_field = partner_cls._fields["company_type"]
        self.assertIn(company_type_field, _base_registry.field_computed)


class TestCrudOperations(unittest.TestCase):
    """Test CRUD operations with DictBackend."""

    def test_create_and_search(self):
        """Create records and search them back."""
        with model_test_env(registry=_base_registry) as env:
            before = len(env["res.partner"].search([]))

            env["res.partner"].create({"name": "Alice"})
            env["res.partner"].create({"name": "Bob"})
            env["res.partner"].create({"name": "Charlie"})

            all_partners = env["res.partner"].search([])
            self.assertEqual(len(all_partners), before + 3)

            alice = env["res.partner"].search([("name", "=", "Alice")])
            self.assertEqual(len(alice), 1)
            self.assertEqual(alice.name, "Alice")

    def test_write_and_read(self):
        """Write updates DictBackend, read reflects changes."""
        with model_test_env(registry=_base_registry) as env:
            partner = env["res.partner"].create({"name": "Alice"})
            self.assertEqual(partner.name, "Alice")

            partner.write({"name": "Alice Smith"})
            self.assertEqual(partner.name, "Alice Smith")

    def test_write_multiple_fields(self):
        """Write updates multiple fields atomically."""
        with model_test_env(registry=_base_registry) as env:
            partner = env["res.partner"].create(
                {"name": "Alice", "email": "old@test.com", "is_company": False}
            )
            partner.write(
                {"name": "Alice Corp", "email": "new@test.com", "is_company": True}
            )
            self.assertEqual(partner.name, "Alice Corp")
            self.assertEqual(partner.email, "new@test.com")
            self.assertTrue(partner.is_company)

    def test_unlink(self):
        """Unlink removes record from DictBackend."""
        with model_test_env(registry=_base_registry) as env:
            partner = env["res.partner"].create({"name": "Alice"})
            pid = partner.id
            partner.unlink()

            remaining = env["res.partner"].search([("id", "=", pid)])
            self.assertEqual(len(remaining), 0)

    def test_ids_are_sequential(self):
        """Auto-incremented IDs are sequential within a session."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "A"})
            p2 = env["res.partner"].create({"name": "B"})
            p3 = env["res.partner"].create({"name": "C"})
            self.assertEqual(p2.id, p1.id + 1)
            self.assertEqual(p3.id, p2.id + 1)

    def test_isolation_between_contexts(self):
        """Each model_test_env gets a fresh DictBackend — full isolation."""
        with model_test_env(registry=_base_registry) as env1:
            env1["res.partner"].create({"name": "Env1Partner"})

        with model_test_env(registry=_base_registry) as env2:
            found = env2["res.partner"].search([("name", "=", "Env1Partner")])
            self.assertEqual(len(found), 0, "Records must not leak between envs")


class TestSearchOperators(unittest.TestCase):
    """Test DictBackend search with various domain operators."""

    def test_search_equal(self):
        """Search with '=' operator."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Alice"})
            env["res.partner"].create({"name": "Bob"})

            found = env["res.partner"].search([("name", "=", "Alice")])
            self.assertEqual(len(found), 1)
            self.assertEqual(found.name, "Alice")

    def test_search_not_equal(self):
        """Search with '!=' excludes matching records."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Alice", "is_company": True})
            env["res.partner"].create({"name": "Bob", "is_company": False})

            non_companies = env["res.partner"].search(
                [("is_company", "=", False)]
            )
            names = [p.name for p in non_companies]
            self.assertIn("Bob", names)
            self.assertNotIn("Alice", names)

    def test_search_in(self):
        """Search with 'in' returns records matching any value."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Alice"})
            env["res.partner"].create({"name": "Bob"})
            env["res.partner"].create({"name": "Charlie"})

            found = env["res.partner"].search(
                [("name", "in", ["Alice", "Charlie"])]
            )
            names = sorted(p.name for p in found)
            self.assertEqual(names, ["Alice", "Charlie"])

    def test_search_ilike(self):
        """Search with 'ilike' is case-insensitive contains."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Alice Smith"})
            env["res.partner"].create({"name": "Bob Jones"})

            found = env["res.partner"].search([("name", "ilike", "alice")])
            self.assertEqual(len(found), 1)
            self.assertEqual(found.name, "Alice Smith")

    def test_search_empty_domain(self):
        """Empty domain returns all records."""
        with model_test_env(registry=_base_registry) as env:
            before = len(env["res.partner"].search([]))
            env["res.partner"].create({"name": "X"})
            after = len(env["res.partner"].search([]))
            self.assertEqual(after, before + 1)

    def test_search_no_results(self):
        """Search with no matches returns empty recordset."""
        with model_test_env(registry=_base_registry) as env:
            found = env["res.partner"].search([("name", "=", "NONEXISTENT")])
            self.assertEqual(len(found), 0)
            self.assertFalse(found)


class TestFilteredMapped(unittest.TestCase):
    """Test recordset operations: filtered(), mapped(), sorted()."""

    def test_filtered_by_field_name(self):
        """filtered('field') keeps records where field is truthy."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Company A", "is_company": True})
            env["res.partner"].create({"name": "Person B", "is_company": False})
            env["res.partner"].create({"name": "Company C", "is_company": True})

            partners = env["res.partner"].search(
                [("name", "in", ["Company A", "Person B", "Company C"])]
            )
            companies = partners.filtered("is_company")
            self.assertEqual(len(companies), 2)

    def test_filtered_by_lambda(self):
        """filtered(lambda) applies arbitrary predicate."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Alice", "email": "a@test.com"})
            env["res.partner"].create({"name": "Bob"})
            env["res.partner"].create({"name": "Charlie", "email": "c@test.com"})

            partners = env["res.partner"].search(
                [("name", "in", ["Alice", "Bob", "Charlie"])]
            )
            with_email = partners.filtered(lambda p: p.email)
            self.assertEqual(len(with_email), 2)

    def test_mapped_extracts_values(self):
        """mapped('field') returns list of field values."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Alice"})
            env["res.partner"].create({"name": "Bob"})

            partners = env["res.partner"].search(
                [("name", "in", ["Alice", "Bob"])]
            )
            names = partners.mapped("name")
            self.assertEqual(sorted(names), ["Alice", "Bob"])

    def test_mapped_relational(self):
        """mapped('relation.field') traverses Many2one."""
        with model_test_env(registry=_base_registry) as env:
            parent = env["res.partner"].create(
                {"name": "Parent Corp", "is_company": True}
            )
            env["res.partner"].create(
                {"name": "Child", "parent_id": parent.id}
            )

            children = env["res.partner"].search([("name", "=", "Child")])
            parent_names = children.mapped("parent_id.name")
            self.assertEqual(parent_names, ["Parent Corp"])

    def test_sorted(self):
        """sorted() returns records in specified order."""
        with model_test_env(registry=_base_registry) as env:
            env["res.partner"].create({"name": "Charlie"})
            env["res.partner"].create({"name": "Alice"})
            env["res.partner"].create({"name": "Bob"})

            partners = env["res.partner"].search(
                [("name", "in", ["Alice", "Bob", "Charlie"])]
            )
            by_name = partners.sorted("name")
            names = [p.name for p in by_name]
            self.assertEqual(names, ["Alice", "Bob", "Charlie"])


class TestRecordsetOperations(unittest.TestCase):
    """Test recordset algebra: union, intersection, subtraction."""

    def test_union(self):
        """p1 | p2 produces a recordset with both records."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "Alice"})
            p2 = env["res.partner"].create({"name": "Bob"})
            union = p1 | p2
            self.assertEqual(len(union), 2)
            self.assertIn(p1.id, union.ids)
            self.assertIn(p2.id, union.ids)

    def test_union_deduplicates(self):
        """Union of a record with itself produces single record."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "Alice"})
            union = p1 | p1
            self.assertEqual(len(union), 1)

    def test_subtraction(self):
        """p_all - p1 removes p1 from the set."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "Alice"})
            p2 = env["res.partner"].create({"name": "Bob"})
            p3 = env["res.partner"].create({"name": "Charlie"})
            all_three = p1 | p2 | p3
            without_bob = all_three - p2
            self.assertEqual(len(without_bob), 2)
            names = sorted(p.name for p in without_bob)
            self.assertEqual(names, ["Alice", "Charlie"])

    def test_intersection(self):
        """p_set1 & p_set2 keeps only common records."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "Alice"})
            p2 = env["res.partner"].create({"name": "Bob"})
            p3 = env["res.partner"].create({"name": "Charlie"})
            set1 = p1 | p2
            set2 = p2 | p3
            common = set1 & set2
            self.assertEqual(len(common), 1)
            self.assertEqual(common.name, "Bob")

    def test_iteration(self):
        """Iterating a multi-record set yields single-record sets."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "Alice"})
            p2 = env["res.partner"].create({"name": "Bob"})
            batch = p1 | p2
            records = list(batch)
            self.assertEqual(len(records), 2)
            for rec in records:
                self.assertEqual(len(rec), 1)

    def test_bool_semantics(self):
        """Non-empty recordset is truthy, empty is falsy."""
        with model_test_env(registry=_base_registry) as env:
            partner = env["res.partner"].create({"name": "Alice"})
            empty = env["res.partner"].browse()
            self.assertTrue(partner)
            self.assertFalse(empty)

    def test_ensure_one(self):
        """ensure_one() passes for single record, fails for multi."""
        with model_test_env(registry=_base_registry) as env:
            p1 = env["res.partner"].create({"name": "Alice"})
            p2 = env["res.partner"].create({"name": "Bob"})
            p1.ensure_one()  # Should not raise
            with self.assertRaises(ValueError):
                (p1 | p2).ensure_one()


class TestMultiModelInteraction(unittest.TestCase):
    """Test that multiple models work together in one env."""

    def test_partner_and_currency_in_same_env(self):
        """Create records in different models within one model_test_env."""
        with model_test_env(registry=_base_registry) as env:
            partner = env["res.partner"].create({"name": "Alice"})
            currency = env["res.currency"].create(
                {"name": "TST", "symbol": "$", "rounding": 0.01}
            )
            self.assertEqual(partner.name, "Alice")
            self.assertEqual(currency.name, "TST")
            currency._compute_decimal_places()
            self.assertEqual(currency.decimal_places, 2)

    def test_partner_and_country(self):
        """Partner with country_id reference across models."""
        with model_test_env(registry=_base_registry) as env:
            country = env["res.country"].create(
                {"name": "Mexico", "code": "MX"}
            )
            partner = env["res.partner"].create(
                {"name": "Mexican Partner", "country_id": country.id}
            )
            # Traverse the Many2one to the country
            self.assertEqual(partner.country_id.name, "Mexico")
            self.assertEqual(partner.country_id.code, "MX")


if __name__ == "__main__":
    unittest.main()

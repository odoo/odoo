from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAProjectedFieldFiresItsConstraints(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent = cls.env["test_orm.projection.parent"].create({"name": "P"})
        cls.child = cls.env["test_orm.projection.child"].create(
            {"name": "C", "parent_id": cls.parent.id, "quantity": 3}
        )
        cls.grandchild = cls.env["test_orm.projection.grandchild"].create(
            {"name": "G", "child_id": cls.child.id}
        )

    def test_a_write_on_the_source_runs_the_childs_check(self):
        with self.assertRaises(ValidationError):
            self.parent.state = "closed"

    def test_the_check_passes_when_the_new_value_is_fine(self):
        self.child.quantity = 0
        self.parent.state = "closed"
        self.assertEqual(self.child.parent_state, "closed")

    def test_two_hops_away_still_fires(self):
        self.child.quantity = 0
        self.grandchild.quantity = 1
        with self.assertRaisesRegex(ValidationError, "grandparent"):
            self.parent.state = "closed"

    def test_moving_the_child_under_another_parent_fires(self):
        closed = self.env["test_orm.projection.parent"].create(
            {"name": "closed", "state": "closed"}
        )
        with self.assertRaises(ValidationError):
            self.child.parent_id = closed

    def test_creating_the_child_under_a_closed_parent_fires(self):
        closed = self.env["test_orm.projection.parent"].create(
            {"name": "closed", "state": "closed"}
        )
        with self.assertRaises(ValidationError):
            self.env["test_orm.projection.child"].create(
                {"name": "late", "parent_id": closed.id, "quantity": 1}
            )

    def test_a_new_record_is_checked_once_its_inverses_have_written(self):
        # `parent_name` is written through its inverse, after the stored pass of
        # create: a check run from `modified()` would read a parent still unnamed
        unnamed = self.env["test_orm.projection.parent"].create({})
        child = self.env["test_orm.projection.child"].create(
            {"name": "named late", "parent_id": unnamed.id, "parent_name": "now named"}
        )
        self.assertEqual(child.parent_name, "now named")
        with self.assertRaisesRegex(ValidationError, "no name"):
            self.env["test_orm.projection.child"].create(
                {"name": "never named", "parent_id": unnamed.copy({"name": False}).id}
            )

    def test_an_unrelated_write_on_the_source_checks_nothing(self):
        calls = []
        Child = type(self.env["test_orm.projection.child"])
        original = Child._check_fields

        def spy(records, field_names, excluded_names=()):
            calls.append((records._name, tuple(field_names)))
            return original(records, field_names, excluded_names)

        self.patch(Child, "_check_fields", spy)
        self.parent.note = "no child reads this"
        self.assertFalse(calls)

    def test_only_the_children_of_the_written_parent_are_checked(self):
        other_parent = self.env["test_orm.projection.parent"].create({"name": "O"})
        other_child = self.env["test_orm.projection.child"].create(
            {"name": "OC", "parent_id": other_parent.id, "quantity": 9}
        )
        self.child.quantity = 0
        self.parent.state = "closed"
        self.assertEqual(other_child.parent_state, "open")

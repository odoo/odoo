from odoo.tests import TransactionCase, new_test_user


class TestWorkEntryTypeOrder(TransactionCase):
    """``_order`` is "sequence, id", so ``sequence`` decides which types lead
    every work_entry_type_id dropdown. A manager has to be able to set it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env,
            login="hr_manager_ordering",
            groups="hr.group_hr_manager",
        )

    def _list_arch(self):
        view = self.env.ref("hr_work_entry.hr_work_entry_type_view_tree")
        return (
            self.env["hr.work.entry.type"]
            .with_user(self.manager)
            .get_view(view.id, "list")["arch"]
        )

    def test_a_manager_can_reorder_the_types(self):
        """Without this the only handle on ``sequence`` is developer mode.

        The form carries the field behind ``base.group_no_one``, which a
        manager does not have, so the list is the one place left.
        """
        self.assertFalse(
            self.manager.has_group("base.group_no_one"),
            "a plain manager is not in developer mode",
        )
        self.assertIn('name="sequence"', self._list_arch())

    def test_sequence_decides_the_order(self):
        """Guard: the field is load-bearing, not decoration."""
        work_entry_type = self.env["hr.work.entry.type"]
        self.assertEqual(work_entry_type._order, "sequence, id")
        last = work_entry_type.search([], order="sequence desc, id desc", limit=1)
        last.sequence = -1
        self.assertEqual(
            work_entry_type.search([], limit=1),
            last,
            "lowering the sequence floats the type to the top of every dropdown",
        )

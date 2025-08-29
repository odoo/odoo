# Copyright (C) 2019 Brian McMaster <brian@mcmpest.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from . import test_fsm_order


class TestFsmCategory(test_fsm_order.TestFSMOrder):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_category_a = cls.env["fsm.category"].create({"name": "Category A"})
        cls.fsm_category_b = cls.env["fsm.category"].create(
            {"name": "Category B", "parent_id": cls.fsm_category_a.id}
        )

    def test_fsm_order_category(self):
        self.assertEqual(self.fsm_category_a.full_name, self.fsm_category_a.name)
        self.assertEqual(
            self.fsm_category_b.full_name,
            f"{self.fsm_category_a.name}/{self.fsm_category_b.name}",
        )

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPartnerOrderCount(TransactionCase):
    """Cover ``base_order``'s res.partner helpers.

    sale and purchase both delegate to these and neither tests them, so the
    behaviour they rely on — counts rolling up from child contacts, archived
    children still counting, the group gate — is pinned here.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Partner = cls.env["res.partner"]
        cls.grandparent = Partner.create({"name": "GP"})
        cls.parent = Partner.create({"name": "P", "parent_id": cls.grandparent.id})
        cls.child = Partner.create({"name": "C", "parent_id": cls.parent.id})
        cls.archived_child = Partner.create(
            {"name": "AC", "parent_id": cls.parent.id, "active": False},
        )

    def _make_orders(self, partner, count):
        return self.env["base.order.test"].create(
            [{"partner_id": partner.id} for _ in range(count)],
        )

    def test_count_rolls_up_through_the_partner_tree(self):
        """An order on a child counts for the child and every ancestor."""
        self._make_orders(self.child, 3)
        self._make_orders(self.parent, 2)
        self._make_orders(self.grandparent, 1)

        self.assertEqual(self.child.base_order_test_count, 3)
        self.assertEqual(self.parent.base_order_test_count, 5, "3 child + 2 own")
        self.assertEqual(
            self.grandparent.base_order_test_count,
            6,
            "3 grandchild + 2 child + 1 own",
        )

    def test_archived_children_still_count(self):
        """The child lookup runs with ``active_test=False`` on purpose."""
        self._make_orders(self.archived_child, 4)

        self.assertEqual(self.archived_child.base_order_test_count, 4)
        self.assertEqual(self.parent.base_order_test_count, 4)
        self.assertEqual(self.grandparent.base_order_test_count, 4)

    def test_count_is_zero_without_the_group(self):
        """Users outside the group get 0, not a filtered count."""
        self._make_orders(self.child, 2)
        portal = self.env["res.users"].create(
            {
                "name": "Portal",
                "login": "bo_portal",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            },
        )
        self.assertFalse(portal.has_group("base.group_user"))

        count = self.child.with_user(portal).sudo().base_order_test_count
        self.assertEqual(count, 0)

    def test_extra_domain_restricts_what_is_counted(self):
        """The ``domain`` argument narrows the counted set."""
        self._make_orders(self.child, 3)
        cancelled = self._make_orders(self.child, 2)
        cancelled.state = "cancel"

        self.child._update_order_count(
            "base.order.test",
            "base_order_test_count",
            "base.group_user",
            domain=[("state", "!=", "cancel")],
        )
        self.assertEqual(self.child.base_order_test_count, 3)

    def test_statistics_tile_is_added_only_when_non_zero(self):
        """``_add_order_statistics`` skips partners with no orders."""
        self._make_orders(self.child, 2)
        partners = self.child | self.parent | self.grandparent
        data_list = {partner.id: [] for partner in partners}

        partners._add_order_statistics(
            data_list,
            "base_order_test_count",
            "base.group_user",
            "fa-solid fa-flask",
            "Test Orders",
            "o_tag_color_1",
        )

        self.assertEqual(
            data_list[self.child.id],
            [
                {
                    "iconClass": "fa-solid fa-flask",
                    "value": 2,
                    "label": "Test Orders",
                    "tagClass": "o_tag_color_1",
                },
            ],
        )
        # ancestors inherit the count, so they get a tile too
        self.assertEqual(len(data_list[self.parent.id]), 1)
        self.assertEqual(data_list[self.parent.id][0]["value"], 2)

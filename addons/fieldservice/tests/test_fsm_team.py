# Copyright (C) 2019 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class FSMTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Order = cls.env["fsm.order"]
        cls.Team = cls.env["fsm.team"]
        cls.test_location = cls.env.ref("fieldservice.test_location")
        cls.test_team = cls.Team.create({"name": "Test Team"})

    def test_fsm_order(self):
        """Test creating new workorders
        - Active orders
        - Unassigned orders
        - Unscheduled orders
        """
        # Create 5 Orders, which are,
        #   - 2 assigned (3 unassigned)
        #   - 4 scheduled (1 unscheduled)
        todo = {"orders": 5, "assigned": [3, 4], "scheduled": [0, 1, 2, 3]}
        view_id = "fieldservice.fsm_order_form"
        self.env.user.groups_id += self.env.ref("fieldservice.group_fsm_team")
        orders = self.Order
        for i in range(todo["orders"]):
            with Form(self.Order, view=view_id) as f:
                f.location_id = self.test_location
                f.team_id = self.test_team
            order = f.save()
            orders += order
            order.person_id = (
                i in todo["assigned"] and self.env.ref("fieldservice.person_1") or False
            )
            order.scheduled_date_start = (
                i in todo["scheduled"] and fields.Datetime.now() or False
            )
        self.assertEqual(
            (
                self.test_team.order_count,
                self.test_team.order_need_assign_count,
                self.test_team.order_need_schedule_count,
            ),
            (5, 3, 1),
        )

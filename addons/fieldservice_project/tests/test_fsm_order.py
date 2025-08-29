# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form

from .common import Common


class TestFsmOrder(Common):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.FsmOrder = cls.env["fsm.order"]

    def test_action_view_order(self):
        order = self.FsmOrder.create({"location_id": self.location.id})
        action = order.action_view_order()
        res_id = action.get("res_id")
        self.assertEqual(res_id, order.id)

    def test_onchange_team_id(self):
        project = self.project
        self.env.user.groups_id += self.env.ref("fieldservice.group_fsm_team")
        team_with_project = self.env["fsm.team"].create(
            {"name": "test team", "project_id": project.id}
        )
        fsm_order_form = Form(self.FsmOrder)
        self.assertFalse(fsm_order_form.project_id)
        fsm_order_form.team_id = team_with_project
        self.assertEqual(fsm_order_form.project_id, project)

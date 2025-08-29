# Copyright (C) 2019 Brian McMaster <brian@mcmpest.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields

from . import test_fsm_order


class TestTemplateOnchange(test_fsm_order.TestFSMOrder):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fsm_category_a = cls.env["fsm.category"].create({"name": "Category A"})
        cls.fsm_category_b = cls.env["fsm.category"].create({"name": "Category B"})
        cls.fsm_type_a = cls.env["fsm.order.type"].create({"name": "FSM Order Type A"})
        cls.fsm_team_a = cls.env["fsm.team"].create({"name": "FSM Team A"})

    def test_fsm_order_onchange_template(self):
        """Test the onchange function for FSM Template
        - Category IDs, Scheduled Duration,and Type should update
        - The instructions should be copied
        """
        categories = []
        categories.append(self.fsm_category_a.id)
        categories.append(self.fsm_category_b.id)
        self.fsm_template_1 = self.env["fsm.template"].create(
            {
                "name": "Test FSM Template #1",
                "instructions": "These are the instructions for Template #1",
                "category_ids": [(6, 0, categories)],
                "duration": 2.25,
                "type_id": self.fsm_type_a.id,
            }
        )
        self.fsm_template_2 = self.env["fsm.template"].create(
            {
                "name": "Test FSM Template #1",
                "instructions": "These are the instructions for Template #1",
                "category_ids": [(6, 0, categories)],
                "duration": 2.25,
                "team_id": self.fsm_team_a.id,
            }
        )
        self.fso = self.Order.create(
            {
                "location_id": self.test_location.id,
                "template_id": self.fsm_template_1.id,
                "scheduled_date_start": fields.Datetime.today(),
            }
        )
        self.fso2 = self.Order.create(
            {
                "location_id": self.test_location.id,
                "template_id": self.fsm_template_2.id,
                "scheduled_date_start": fields.Datetime.today(),
            }
        )
        self.fso._onchange_template_id()
        self.fso2._onchange_template_id()
        self.assertEqual(
            self.fso.category_ids.ids, self.fsm_template_1.category_ids.ids
        )
        self.assertEqual(self.fso.scheduled_duration, self.fsm_template_1.duration)
        self.assertEqual(self.fso.type.id, self.fsm_template_1.type_id.id)
        self.assertEqual(self.fso.todo, self.fsm_template_1.instructions)
        self.assertEqual(self.fso2.team_id.id, self.fsm_team_a.id)

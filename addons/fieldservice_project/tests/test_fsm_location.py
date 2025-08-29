# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common import Common


class TestFsmLocation(Common):
    def test_project_count(self):
        location = self.location
        project = self.project
        self.assertEqual(location.project_count, 0)
        project.write({"fsm_location_id": location.id})
        location.invalidate_model()
        self.assertEqual(location.project_count, 1)

    def test_action_view_project(self):
        location = self.location
        project = self.project
        action = location.action_view_project()
        action_domain = action.get("domain")
        res_id = action.get("res_id")
        self.assertEqual(action_domain, [("id", "in", [])])
        self.assertFalse(res_id)
        project.write({"fsm_location_id": location.id})
        action = location.action_view_project()
        res_id = action.get("res_id")
        self.assertEqual(res_id, project.id)

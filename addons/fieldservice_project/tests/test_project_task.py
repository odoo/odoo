# Copyright 2021 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from .common import Common


class TestProjectTask(Common):
    def test_action_create_order(self):
        project = self.project
        task = self.env["project.task"].create(
            {"name": "task test", "project_id": project.id}
        )
        action = task.action_create_order()
        self.assertDictEqual(
            action.get("context"),
            {
                "default_project_id": project.id,
                "default_project_task_id": task.id,
                "default_location_id": project.fsm_location_id.id,
                "default_origin": task.name,
            },
        )

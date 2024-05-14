import { models } from "@web/../tests/web_test_helpers";

export class ProjectProject extends models.ServerModel {
    _name = "project.project";

    _records = [
        { active: true, name: "Project B", last_update_status: "on_track", last_update_color: 20},
    ];
}

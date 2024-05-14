import { models } from "@web/../tests/web_test_helpers";

export class ProjectUpdate extends models.ServerModel {
    _name = "project.update";

    _records = [
        { status: "on_track" },
    ];
}

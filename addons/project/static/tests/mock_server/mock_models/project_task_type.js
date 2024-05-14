import { models } from "@web/../tests/web_test_helpers";

export class ProjectTaskType extends models.ServerModel {
    _name = "project.task.type";

    _records = [
        { id: 1, name: "Todo" },
        { id: 2, name: "In Progress" },
        { id: 3, name: "Done" },
    ];
}

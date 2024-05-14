import { models } from "@web/../tests/web_test_helpers";

export class ProjectProjectStage extends models.ServerModel {
    _name = "project.project.stage";

    _records = [
        { id: 1, name: "Todo" },
        { id: 2, name: "In Progress" },
        { id: 3, name: "Done" },
    ];
}

import { fields } from "@web/../tests/web_test_helpers";
import { projectModels } from "@project/../tests/project_models";

export class ProjectTask extends projectModels.ProjectTask {
    _name = "project.task";

    company_id = fields.Many2one({ string: "Company", relation: "res.company" });
    tag_ids = fields.Many2many({ relation: "project.tags" });

    _records = [
        {
            id: 1,
            name: "Todo 1",
            state: "01_in_progress",
            tag_ids: [1],
        },
        {
            id: 2,
            name: "Todo 2",
            state: "1_done",
            tag_ids: [3],
        },
        {
            id: 3,
            name: "Todo 3",
            state: "01_in_progress",
            tag_ids: [3, 2],
        },
    ];
}

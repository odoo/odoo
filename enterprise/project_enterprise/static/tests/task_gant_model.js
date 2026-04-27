import { projectModels } from "@project/../tests/project_models";
import { fields } from "@web/../tests/web_test_helpers";

export class ProjectTask extends projectModels.ProjectTask {
    _name = "project.task";

    planned_date_begin = fields.Datetime({ string: "Start Date" });
    planned_date_end = fields.Datetime({ string: "End Date" });
    planning_overlap = fields.Html();
    planned_date_start = fields.Date({ string: "Date Start" });
    partner_id = fields.Many2one({ string: "Partner", relation: "res.partner" });
    start = fields.Datetime({ string: "Start Date" });
    stop = fields.Datetime({ string: "Stop Date" });
}

projectModels.ProjectTask = ProjectTask;

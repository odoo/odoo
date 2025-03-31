import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class ProjectProject extends models.Model {
    _name = "project.project";

    name = fields.Char();
    is_favorite = fields.Boolean();

    _records = [
        { id: 1, name: "Project 1" },
        { id: 2, name: "Project 2" },
    ];
}

export class ProjectTask extends models.Model {
    _name = "project.task";

    name = fields.Char();
    parent_id = fields.Many2one({ relation: "project.task" });
    child_ids = fields.One2many({
        relation: "project.task",
        relation_field: "parent_id",
    });
    subtask_count = fields.Integer();
    closed_subtask_count = fields.Integer();
    project_id = fields.Many2one({ relation: "project.project" });
    display_in_project = fields.Boolean();
    stage_id = fields.Many2one({ relation: "project.task.type" });
    milestone_id = fields.Many2one({ relation: "project.milestone" });
    state = fields.Selection({
        selection: [
            ["01_in_progress", "In Progress"],
            ["02_changes_requested", "Changes Requested"],
            ["03_approved", "Approved"],
            ["04_waiting_normal", "Waiting Normal"],
        ],
    });
    user_ids = fields.Many2many({
        string: "Assignees",
        relation: "res.users",
    });
    priority = fields.Selection({
        selection: [
            ["0", "Low"],
            ["1", "High"],
        ],
    });
    planned_date_begin = fields.Datetime({ string: "Start Date" });
    date_deadline = fields.Datetime({ string: "Stop Date" });
    depend_on_ids = fields.Many2many({ relation: "project.task" });
    closed_depend_on_count = fields.Integer();

    _records = [
        {
            id: 1,
            name: "Regular task 1",
            project_id: 1,
            stage_id: 1,
            milestone_id: 1,
            state: "01_in_progress",
            user_ids: [7],
        },
        {
            id: 2,
            name: "Regular task 2",
            project_id: 1,
            stage_id: 1,
            state: "03_approved",
        },
        {
            id: 3,
            name: "Private task 1",
            project_id: false,
            stage_id: 1,
            state: "04_waiting_normal",
        },
    ];
}

export class ProjectTaskType extends models.Model {
    _name = "project.task.type";

    name = fields.Char();
    sequence = fields.Integer();

    _records = [
        { id: 1, name: "Todo" },
        { id: 2, name: "In Progress" },
        { id: 3, name: "Done" },
    ];
}

export class ProjectMilestone extends models.Model {
    _name = "project.milestone";

    name = fields.Char();

    _records = [{ id: 1, name: "Milestone 1" }];
}

export function defineProjectModels() {
    defineMailModels();
    defineModels(projectModels);
}

export const projectModels = {
    ProjectProject,
    ProjectTask,
    ProjectTaskType,
    ProjectMilestone,
};

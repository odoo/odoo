import { defineProjectModels, projectModels } from "@project/../tests/project_models";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class HRTimesheet extends models.Model {
    _name = "account.analytic.line";

    project_id = fields.Many2one({ relation: "project.project" });
    task_id = fields.Many2one({ relation: "project.task" });
    unit_amount = fields.Float();

    _records = [
        {
            id: 1,
            project_id: 1,
            task_id: 3,
            unit_amount: 1,
        },
        {
            id: 2,
            project_id: 1,
            task_id: false,
            unit_amount: 2,
        },
        {
            id: 3,
            project_id: false,
            task_id: false,
            unit_amount: 5,
        },
    ];
    _views = {
        form: `
            <form>
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="unit_amount"/>
            </form>
        `,
        list: `
            <tree editable="bottom">
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="unit_amount"/>
            </tree>
        `,
        graph: `
            <graph js_class="hr_timesheet_graphview">
                <field name="unit_amount"/>
                <field name="unit_amount" type="measure"/>
            </graph>
        `,
    };
}

export class ProjectTask extends projectModels.ProjectTask {
    progress = fields.Float();

    _records = [
        {
            id: 1,
            name: "Task 1\u00A0AdditionalInfo",
            project_id: 1,
            progress: 0.5,
        },
        {
            id: 2,
            name: "Task 2\u00A0AdditionalInfo",
            project_id: 1,
            progress: 0.8,
        },
        {
            id: 3,
            name: "Task 3\u00A0AdditionalInfo",
            project_id: 1,
            progress: 1.04,
        },
    ];
}

projectModels.ProjectTask = ProjectTask;

export function defineTimesheetModels() {
    defineProjectModels();
    defineModels([HRTimesheet]);
}

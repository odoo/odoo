import { mockDate } from "@odoo/hoot-mock";
import { session } from "@web/session";
import { defineModels, fields, models, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { defineProjectModels, projectModels } from "@project/../tests/project_models";

export class HRTimesheet extends models.Model {
    _name = "account.analytic.line";

    name = fields.Char();
    project_id = fields.Many2one({ relation: "project.project", required: true });
    task_id = fields.Many2one({ relation: "project.task" });
    unit_amount = fields.Float();
    is_timesheet = fields.Boolean();

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

export class ProjectProject extends projectModels.ProjectProject {
    get_create_edit_project_ids() {
        return [];
    }
}

projectModels.ProjectTask = ProjectTask;
projectModels.ProjectProject = ProjectProject;

export const hrTimesheetModels = { HRTimesheet };

export function defineTimesheetModels() {
    defineProjectModels();
    defineModels(hrTimesheetModels);
}

export function patchSession() {
    mockDate("2017-01-25 00:00:00");
    patchWithCleanup(session, {
        user_companies: {
            current_company: 1,
            allowed_companies: {
                1: {
                    id: 1,
                    name: "Company",
                    timesheet_uom_id: 1,
                    timesheet_uom_factor: 1,
                },
            },
        },
        uom_ids: {
            1: {
                id: 1,
                name: "hour",
                rounding: 0.01,
                timesheet_widget: "float_time",
            },
            2: {
                id: 2,
                name: "day",
                rounding: 0.01,
                timesheet_widget: "float_toggle",
            },
            3: {
                id: 3,
                name: "foo",
                rounding: 0.01,
                timesheet_widget: "float_factor",
            },
        },
    });
}

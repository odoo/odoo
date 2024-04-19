import { test } from "@odoo/hoot";
import { session } from "@web/session";
import { mountView, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { HRTimesheet, ProjectTask, defineTimesheetModels } from "./hr_timesheet_models";
import {
    checkDatasets,
    checkLabels,
    checkLegend,
    selectMode,
} from "@web/../tests/views/graph/graph_test_helpers";

defineTimesheetModels();

test("hr.timesheet (graph): data are not multiplied by a company related factor (factor === 1)", async () => {
    patchWithCleanup(session.user_companies.allowed_companies[1], {
        timesheet_uom_factor: 1,
    });

    const graph = await mountView({
        resModel: "account.analytic.line",
        type: "graph",
    });

    checkDatasets(graph, "data", { data: [8] });
});

test("hr.timesheet (graph): data are multiplied by a company related factor (factor !== 1)", async () => {
    patchWithCleanup(session.user_companies.allowed_companies[1], {
        timesheet_uom_factor: 0.125,
    });

    const graph = await mountView({
        resModel: "account.analytic.line",
        type: "graph",
    });

    checkDatasets(graph, "data", { data: [1] });
});

test("project.task (graph): check custom default label", async () => {
    HRTimesheet._records = [];
    ProjectTask._records = [
        { id: 1, name: "Task 1", project_id: 1, milestone_id: 1 },
        { id: 2, name: "Task 2", project_id: false, milestone_id: false },
    ];

    const graph = await mountView({
        resModel: "project.task",
        type: "graph",
        arch: `
            <graph js_class="hr_timesheet_graphview">
                <field name="project_id"/>
            </graph>
        `,
    });

    checkLabels(graph, ["Project 1", "🔒 Private"]);
    checkLegend(graph, ["Count"]);

    await selectMode("line");

    checkLabels(graph, ["", "Project 1", ""]);
    checkLegend(graph, ["Count"]);

    await selectMode("pie");

    checkLabels(graph, ["Project 1", "🔒 Private"]);
    checkLegend(graph, ["Project 1", "🔒 Private"]);
});

test("project.task (graph): check default label with 2 fields in groupby", async () => {
    HRTimesheet._records = [];
    ProjectTask._records = [
        { id: 1, name: "Task 1", project_id: 1, milestone_id: 1 },
        { id: 2, name: "Task 2", project_id: false, milestone_id: false },
    ];

    const graph = await mountView({
        resModel: "project.task",
        type: "graph",
        arch: `
            <graph js_class="hr_timesheet_graphview">
                <field name="project_id"/>
                <field name="milestone_id"/>
            </graph>
        `,
    });

    checkLabels(graph, ["Project 1", "🔒 Private"]);
    checkLegend(graph, ["Milestone 1", "None", "Sum"]);

    await selectMode("line");

    checkLabels(graph, ["", "Project 1", ""]);
    checkLegend(graph, ["Milestone 1"]);

    await selectMode("pie");

    checkLabels(graph, ["Project 1 / Milestone 1", "🔒 Private / None"]);
    checkLegend(graph, ["Project 1 / Milestone 1", "🔒 Private / None"]);
});

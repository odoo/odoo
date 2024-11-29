import { test, beforeEach } from "@odoo/hoot";
import { mountView } from "@web/../tests/web_test_helpers";
import { checkLabels, checkLegend, selectMode } from "@web/../tests/views/graph/graph_test_helpers";

import { defineProjectModels, ProjectTask } from "./project_models";

defineProjectModels();
beforeEach(() => {
    ProjectTask._records = [
        {
            id: 1,
            name: "Task 1",
            project_id: 1,
            milestone_id: 1,
        },
        {
            id: 2,
            name: "Task 2",
            project_id: false,
            milestone_id: false,
        },
    ];
});

test("project.task (graph): check custom default label", async () => {
    const graph = await mountView({
        resModel: "project.task",
        type: "graph",
        arch: `
            <graph js_class="project_task_graph">
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
    const graph = await mountView({
        resModel: "project.task",
        type: "graph",
        arch: `
            <graph js_class="project_task_graph">
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

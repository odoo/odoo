/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { checkLabels, checkLegend, selectMode } from "@web/../tests/views/graph_view_tests";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData, target;

QUnit.module("Project", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                "project.task": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                        milestone_id: {
                            string: "Milestone",
                            type: "many2one",
                            relation: "project.milestone",
                            store: true,
                            sortable: true,
                        },
                        project_id: {
                            string: "Project",
                            type: "many2one",
                            relation: "project.project",
                            store: true,
                            sortable: true,
                        },
                    },
                    records: [
                        { id: 1, name: "Task 1", project_id: 1, milestone_id: 1 },
                        { id: 2, name: "Task 2", project_id: false, milestone_id: false },
                    ],
                },
                "project.milestone": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", "type": "char" },
                    },
                    records: [
                        { id: 1, name: "Milestone 1" },
                    ]
                },
                "project.project": {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", "type": "char" },
                    },
                    records: [
                        { id: 1, name: "Project 1" },
                    ],
                },
            },
            views: {},
        };
        setupViewRegistries();

        target = getFixture();
    });

    QUnit.module("ProjectTaskGraphView");

    QUnit.test("check custom default label", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "project.task",
            arch: `
                <graph js_class="project_task_graph">
                    <field name="project_id"/>
                </graph>
            `,
        });

        checkLabels(assert, graph, ["🔒 Private", "Project 1"]);
        checkLegend(assert, graph, ["Count"]);

        await selectMode(target, "line");

        checkLabels(assert, graph, ["", "Project 1", ""]);
        checkLegend(assert, graph, ["Count"]);

        await selectMode(target, "pie");

        checkLabels(assert, graph, ["🔒 Private", "Project 1"]);
        checkLegend(assert, graph, ["🔒 Private", "Project 1"]);
    });

    QUnit.test("check default label with 2 fields in groupby", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "project.task",
            arch: `
                <graph js_class="project_task_graph">
                    <field name="project_id"/>
                    <field name="milestone_id"/>
                </graph>
            `,
        });

        checkLabels(assert, graph, ["🔒 Private", "Project 1"]);
        checkLegend(assert, graph, ["None", "Milestone 1", "Sum"]);

        await selectMode(target, "line");

        checkLabels(assert, graph, ["", "Project 1", ""]);
        checkLegend(assert, graph, ["Milestone 1"]);

        await selectMode(target, "pie");

        checkLabels(assert, graph, [
            "🔒 Private / None",
            "Project 1 / Milestone 1"
        ]);
        checkLegend(assert, graph, [
            "🔒 Private / None",
            "Project 1 / Milestone 1"
        ]);
    });
});

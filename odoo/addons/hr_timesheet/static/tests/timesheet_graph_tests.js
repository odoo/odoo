/** @odoo-module **/

import { companyService } from "@web/webclient/company_service";
import {
    checkLabels,
    checkLegend,
    getGraphRenderer,
    selectMode
} from "@web/../tests/views/graph_view_tests";
import { makeView } from "@web/../tests/views/helpers";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { setupControlPanelServiceRegistry } from "@web/../tests/search/helpers";

const serviceRegistry = registry.category("services");

QUnit.module('hr_timesheet', function (hooks) {
    let serverData, target;
    hooks.beforeEach(() => {
        serverData = {
            models: {
                'account.analytic.line': {
                    fields: {
                        unit_amount: { string: "Unit Amount", type: "float", group_operator: "sum", store: true },
                        project_id: {
                            string: "Project",
                            type: "many2one",
                            relation: "project.project",
                            store: true,
                            sortable: true,
                        },
                    },
                    records: [
                        { id: 1, unit_amount: 8, project_id: false },
                    ],
                },
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
            views: {
                // unit_amount is used as group_by and measure
                "account.analytic.line,false,graph": `
                    <graph>
                        <field name="unit_amount"/>
                        <field name="unit_amount" type="measure"/>
                    </graph>
                `,
            }
        }
        setupControlPanelServiceRegistry();
        target = getFixture();
        serviceRegistry.add("company", companyService, { force: true });
    });

    QUnit.module("hr_timesheet_graphview");

    QUnit.test('the timesheet graph view data are not multiplied by a factor that is company related (factor = 1)', async function (assert) {
        assert.expect(1);

        patchWithCleanup(session.user_companies.allowed_companies[1], {
            timesheet_uom_factor: 1,
        });

        const graph = await makeView({
            serverData,
            resModel: "account.analytic.line",
            type: "hr_timesheet_graphview",
        });

        const renderedData = getGraphRenderer(graph).chart.data.datasets[0].data;
        assert.deepEqual(renderedData, [8], 'The timesheet graph view is taking the timesheet_uom_factor into account (factor === 1)');
    });

    QUnit.test('the timesheet graph view data are multiplied by a factor that is company related (factor !== 1)', async function (assert) {
        assert.expect(1);

        patchWithCleanup(session.user_companies.allowed_companies[1], {
            timesheet_uom_factor: 0.125,
        });

        const graph = await makeView({
            serverData,
            resModel: "account.analytic.line",
            type: "hr_timesheet_graphview",
        });

        const renderedData = getGraphRenderer(graph).chart.data.datasets[0].data;
        assert.deepEqual(renderedData, [1], 'The timesheet graph view is taking the timesheet_uom_factor into account (factor !== 1)');
    });

    QUnit.test("check custom default label", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "project.task",
            arch: `
                <graph js_class="hr_timesheet_graphview">
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
                <graph js_class="hr_timesheet_graphview">
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

/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { start } from "@mail/../tests/helpers/test_utils";
import { checkLabels, checkLegend, selectMode } from "@web/../tests/views/graph_view_tests";
import {
    patchDialog,
    getColumn,
    toggleColumnActions,
    createColumn,
} from "@web/../tests/views/kanban/helpers";

let target;
let serverData;

QUnit.module("helpdesk", (hooks) => {
    hooks.beforeEach(async () => {
        const pyEnv = await startServer();
        pyEnv.mockServer.models["helpdesk.stage"] = {
            fields: {
                id: { string: "ID", type: "integer" },
                display_name: { string: "Name", type: "char" },
            },
            records: [
                { id: 1, display_name: "Stage 1" },
                { id: 2, display_name: "Stage 2" },
                { id: 3, display_name: "Stage 3" },
            ],
        };
        pyEnv.mockServer.models["helpdesk.team"] = {
            fields: {
                id: { string: "ID", type: "integer" },
                display_name: { string: "Name", type: "char" },
            },
            records: [{ id: 1, display_name: "Team 1" }],
        };
        pyEnv.mockServer.models["helpdesk.ticket"] = {
            fields: {
                id: { string: "Id", type: "integer" },
                name: { string: "Name", type: "char" },
                sla_deadline: {
                    string: "SLA Deadline",
                    type: "date",
                    store: true,
                    sortable: true,
                },
                team_id: { string: "Team", type: "many2one", relation: "helpdesk.team" },
                stage_id: { string: "Stage", type: "many2one", relation: "helpdesk.stage" },
            },
            records: [
                { id: 1, name: "My ticket", sla_deadline: false, team_id: 1, stage_id: 1 },
                { id: 2, name: "Ticket 2", team_id: 1, stage_id: 1 },
                { id: 3, name: "Ticket 3", team_id: 1, stage_id: 2 },
            ],
        };
        serverData = {
            views: {
                "helpdesk.ticket,false,kanban": `
                    <kanban default_group_by="stage_id" js_class="helpdesk_ticket_kanban">
                        <field name="stage_id"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="name"/>
                                    <field name="sla_deadline"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>
                `,
                "helpdesk.ticket,1,kanban": `<kanban js_class="helpdesk_ticket_kanban" default_group_by="sla_deadline">
                        <templates>
                            <t t-name="kanban-box"/>
                        </templates>
                    </kanban>`,
                "helpdesk.ticket,false,graph": `<graph/>`,
                "helpdesk.ticket,false,search": `<search/>`,
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("helpdesk_ticket_list");

    QUnit.test("Test group label for empty SLA Deadline in tree", async function (assert) {
        const views = {
            "helpdesk.ticket,false,list": `<tree js_class="helpdesk_ticket_list">
                    <field name="sla_deadline" widget="remaining_days"/>
                </tree>`,
            "helpdesk.ticket,false,search": `<search/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "tree"]],
            context: { group_by: ["sla_deadline"] },
        });

        assert.strictEqual(target.querySelector(".o_group_name").innerText, "Deadline reached (3)");
    });

    QUnit.module("helpdesk_ticket_kanban");

    QUnit.test("Test group label for empty SLA Deadline in kanban", async function (assert) {
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[1, "kanban"]],
        });

        assert.strictEqual(target.querySelector(".o_column_title").innerText, "Deadline reached");
    });

    QUnit.test("delete a column in grouped on m2o", async function (assert) {
        let dialogProps;

        patchDialog((_cls, props) => {
            assert.ok(true, "a confirm modal should be displayed");
            dialogProps = props;
        });

        const { openView } = await start({
            serverData,
            async mockRPC(route, { ids, method, model }) {
                if (model === "helpdesk.stage" && method === "action_unlink_wizard") {
                    assert.step(`${model}/${method}`);
                    return {
                        type: "ir.actions.client",
                        tag: "reload",
                    };
                }
            },
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "kanban"]],
        });

        assert.containsN(target, ".o_kanban_group", 2, "should have 2 columns");
        assert.strictEqual(
            getColumn(target, 0).querySelector(".o_column_title").innerText,
            "Stage 1"
        );
        assert.strictEqual(
            getColumn(target, 1).querySelector(".o_column_title").innerText,
            "Stage 2"
        );
        assert.containsN(getColumn(target, 0), ".o_kanban_record", 2);
        assert.containsN(getColumn(target, 1), ".o_kanban_record", 1);

        const clickColumnAction = await toggleColumnActions(target, 1);
        await clickColumnAction("Delete");
        assert.strictEqual(dialogProps, undefined, "No dialog should be displayed");
        assert.verifySteps(["helpdesk.stage/action_unlink_wizard"]);
    });

    QUnit.test(
        "Cannot create group if we are not in tickets of specific helpdesk team",
        async function (assert) {
            const { openView } = await start({
                serverData,
            });
            await openView({
                res_model: "helpdesk.ticket",
                views: [[false, "kanban"]],
            });

            assert.containsN(target, ".o_kanban_group", 2);
            assert.containsNone(
                target,
                ".o_column_quick_create",
                "should have no quick create column"
            );
        }
    );

    QUnit.test("Can create group if we are a specific helpdesk team", async function (assert) {
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "kanban"]],
            context: {
                active_model: "helpdesk.team",
                active_id: 1,
            },
        });

        assert.containsN(target, ".o_kanban_group", 2);
        assert.containsOnce(target, ".o_column_quick_create", "should have no quick create column");
        assert.containsNone(
            target,
            ".o_column_quick_create input",
            "the input should not be visible"
        );

        await createColumn(target);

        assert.containsOnce(target, ".o_column_quick_create input", "the input should be visible");
    });
    QUnit.module("helpdesk_ticket_pivot");

    QUnit.test("Test group label for empty SLA Deadline in pivot", async function (assert) {
        const views = {
            "helpdesk.ticket,false,pivot": `<pivot js_class="helpdesk_ticket_pivot">
                    <field name="sla_deadline" type="row"/>
                </pivot>`,
            "helpdesk.ticket,false,search": `<search/>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "helpdesk.ticket",
            views: [[false, "pivot"]],
        });

        assert.strictEqual(
            target.querySelector("tr:nth-of-type(2) .o_pivot_header_cell_closed").innerText,
            "Deadline reached"
        );
    });

    QUnit.module("helpdesk_ticket_graph");

    QUnit.test("Test group label for empty SLA Deadline in graph", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "helpdesk.ticket",
            groupBy: ["sla_deadline"],
            arch: `
                <graph js_class="helpdesk_ticket_graph">
                    <field name="sla_deadline"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="group_by_sla_deadline" string="SLA Deadline" context="{ 'group_by': 'sla_deadline:day' }"/>
                </search>
            `,
        });
        checkLabels(assert, graph, ["Deadline reached"]);
        checkLegend(assert, graph, ["Count"]);

        await selectMode(target, "pie");

        checkLabels(assert, graph, ["Deadline reached"]);
        checkLegend(assert, graph, ["Deadline reached"]);
    });
});

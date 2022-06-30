/** @odoo-module **/

import { click, getFixture, nextTick, triggerEvent } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("Fields", (hooks) => {
    const graph_values = [
        { value: 300, label: "5-11 Dec" },
        { value: 500, label: "12-18 Dec" },
        { value: 100, label: "19-25 Dec" },
    ];

    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        graph_data: { string: "Graph Data", type: "text" },
                        graph_type: {
                            string: "Graph Type",
                            type: "selection",
                            selection: [
                                ["line", "Line"],
                                ["bar", "Bar"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            int_field: 10,
                            selection: "blocked",
                            graph_type: "bar",
                            graph_data: JSON.stringify([
                                {
                                    color: "blue",
                                    title: "Partner 1",
                                    values: graph_values,
                                    key: "A key",
                                    area: true,
                                },
                            ]),
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            int_field: 0,
                            selection: "normal",
                            graph_type: "line",
                            graph_data: JSON.stringify([
                                {
                                    color: "red",
                                    title: "Partner 0",
                                    values: graph_values,
                                    key: "A key",
                                    area: true,
                                },
                            ]),
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    async function reloadKanbanView(target) {
        await click(target, "input.o_searchview_input");
        await triggerEvent(target, "input.o_searchview_input", "keydown", { key: "Enter" });
    }
    // Kanban
    // WOWL remove this helper and user the control panel instead
    const reload = async (kanban, params = {}) => {
        kanban.env.searchModel.reload(params);
        kanban.env.searchModel.search();
        await nextTick();
    };

    QUnit.module("JournalDashboardGraphField");

    QUnit.test("JournalDashboardGraphField is rendered correctly", async function (assert) {
        await makeView({
            serverData,
            type: "kanban",
            resModel: "partner",
            arch: `
                <kanban>
                    <field name="graph_type"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            domain: [["id", "in", [1, 2]]],
        });
        assert.containsN(
            target,
            ".o_dashboard_graph canvas",
            2,
            "there should be two graphs rendered"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(1) .o_graph_barchart",
            "graph of first record should be a barchart"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(2) .o_graph_linechart",
            "graph of second record should be a linechart"
        );

        await reloadKanbanView(target);
        assert.containsN(
            target,
            ".o_dashboard_graph canvas",
            2,
            "there should be two graphs rendered"
        );
    });

    QUnit.test(
        "rendering of a JournalDashboardGraphField in an updated grouped kanban view",
        async function (assert) {
            const kanban = await makeView({
                serverData,
                type: "kanban",
                resModel: "partner",
                arch: `
                    <kanban>
                        <field name="graph_type"/>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
                domain: [["id", "in", [1, 2]]],
            });
            assert.containsN(
                target,
                ".o_dashboard_graph canvas",
                2,
                "there should be two graph rendered"
            );

            await reload(kanban, { groupBy: ["selection"], domain: [["int_field", "=", 10]] });

            assert.containsOnce(
                target,
                ".o_dashboard_graph canvas",
                "there should be one graph rendered"
            );
        }
    );
});

/** @odoo-module **/

import { click, editInput } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    var graph_values = [
        { value: 300, label: "5-11 Dec" },
        { value: 500, label: "12-18 Dec" },
        { value: 100, label: "19-25 Dec" },
    ];
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
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

    QUnit.module("JournalDashboardGraphField", {
        beforeEach: function () {
            _.extend(this.data.partner.fields, {
                graph_data: { string: "Graph Data", type: "text" },
                graph_type: {
                    string: "Graph Type",
                    type: "selection",
                    selection: [
                        ["line", "Line"],
                        ["bar", "Bar"],
                    ],
                },
            });
            this.data.partner.records[0].graph_type = "bar";
            this.data.partner.records[1].graph_type = "line";
            var graph_values = [
                { value: 300, label: "5-11 Dec" },
                { value: 500, label: "12-18 Dec" },
                { value: 100, label: "19-25 Dec" },
            ];
            this.data.partner.records[0].graph_data = JSON.stringify([
                {
                    color: "red",
                    title: "Partner 0",
                    values: graph_values,
                    key: "A key",
                    area: true,
                },
            ]);
            this.data.partner.records[1].graph_data = JSON.stringify([
                {
                    color: "blue",
                    title: "Partner 1",
                    values: graph_values,
                    key: "A key",
                    area: true,
                },
            ]);
        },
    });

    QUnit.skip("JournalDashboardGraphField attach/detach callbacks", async function (assert) {
        // This widget is rendered with Chart.js.
        var done = assert.async();
        assert.expect(6);

        /*testUtils.mock.patch(JournalDashboardGraph, {
            on_attach_callback: function () {
                assert.step("on_attach_callback");
            },
            on_detach_callback: function () {
                assert.step("on_detach_callback");
            },
        });*/

        makeView({
            serverData,
            type: "kanban",
            resModel: "partner",
            arch:
                '<kanban class="o_kanban_test">' +
                '<field name="graph_type"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                "</div>" +
                "</t>" +
                "</templates></kanban>",
            domain: [["id", "in", [1, 2]]],
        });
        /*.then(function (kanban) {
            assert.verifySteps(["on_attach_callback", "on_attach_callback"]);

            kanban.on_detach_callback();

            assert.verifySteps(["on_detach_callback", "on_detach_callback"]);

            kanban.destroy();
            testUtils.mock.unpatch(JournalDashboardGraph);
            done();
        });*/
    });

    QUnit.skip("JournalDashboardGraphField is rendered correctly", async function (assert) {
        var done = assert.async();
        assert.expect(3);

        createView({
            View: KanbanView,
            model: "partner",
            data: this.data,
            arch:
                '<kanban class="o_kanban_test">' +
                '<field name="graph_type"/>' +
                '<templates><t t-name="kanban-box">' +
                "<div>" +
                '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                "</div>" +
                "</t>" +
                "</templates></kanban>",
            domain: [["id", "in", [1, 2]]],
        }).then(function (kanban) {
            concurrency
                .delay(0)
                .then(function () {
                    assert.strictEqual(
                        kanban.$(".o_kanban_record:first() .o_graph_barchart").length,
                        1,
                        "graph of first record should be a barchart"
                    );
                    assert.strictEqual(
                        kanban.$(".o_kanban_record:nth(1) .o_dashboard_graph").length,
                        1,
                        "graph of second record should be a linechart"
                    );

                    // force a re-rendering of the first record (to check if the
                    // previous rendered graph is correctly removed from the DOM)
                    var firstRecordState = kanban.model.get(kanban.handle).data[0];
                    return kanban.renderer.updateRecord(firstRecordState);
                })
                .then(function () {
                    return concurrency.delay(0);
                })
                .then(function () {
                    assert.strictEqual(
                        kanban.$(".o_kanban_record:first() canvas").length,
                        1,
                        "there should be only one rendered graph by record"
                    );

                    kanban.destroy();
                    done();
                });
        });
    });

    QUnit.skip(
        "rendering of a field with JournalDashboardGraphField in an updated kanban view (ungrouped)",
        async function (assert) {
            var done = assert.async();
            assert.expect(2);

            createView({
                View: KanbanView,
                model: "partner",
                data: this.data,
                arch:
                    '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                    "<div>" +
                    '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                    "</div>" +
                    "</t>" +
                    "</templates></kanban>",
                domain: [["id", "in", [1, 2]]],
            }).then(function (kanban) {
                concurrency
                    .delay(0)
                    .then(function () {
                        assert.containsN(
                            kanban,
                            ".o_dashboard_graph canvas",
                            2,
                            "there should be two graph rendered"
                        );
                        return kanban.update({});
                    })
                    .then(function () {
                        return concurrency.delay(0); // one graph is re-rendered
                    })
                    .then(function () {
                        assert.containsN(
                            kanban,
                            ".o_dashboard_graph canvas",
                            2,
                            "there should be one graph rendered"
                        );
                        kanban.destroy();
                        done();
                    });
            });
        }
    );

    QUnit.skip(
        "rendering of a field with JournalDashboardGraphField in an updated kanban view (grouped)",
        async function (assert) {
            var done = assert.async();
            assert.expect(2);

            createView({
                View: KanbanView,
                model: "partner",
                data: this.data,
                arch:
                    '<kanban class="o_kanban_test">' +
                    '<field name="graph_type"/>' +
                    '<templates><t t-name="kanban-box">' +
                    "<div>" +
                    '<field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>' +
                    "</div>" +
                    "</t>" +
                    "</templates></kanban>",
                domain: [["id", "in", [1, 2]]],
            }).then(function (kanban) {
                concurrency
                    .delay(0)
                    .then(function () {
                        assert.containsN(
                            kanban,
                            ".o_dashboard_graph canvas",
                            2,
                            "there should be two graph rendered"
                        );
                        return kanban.update({
                            groupBy: ["selection"],
                            domain: [["int_field", "=", 10]],
                        });
                    })
                    .then(function () {
                        assert.containsOnce(
                            kanban,
                            ".o_dashboard_graph canvas",
                            "there should be one graph rendered"
                        );
                        kanban.destroy();
                        done();
                    });
            });
        }
    );
});

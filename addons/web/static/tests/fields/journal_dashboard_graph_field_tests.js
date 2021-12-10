/** @odoo-module **/

import { setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
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
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
                        },
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
                            value: "",
                            lang: "en_US",
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

        testUtils.mock.patch(JournalDashboardGraph, {
            on_attach_callback: function () {
                assert.step("on_attach_callback");
            },
            on_detach_callback: function () {
                assert.step("on_detach_callback");
            },
        });

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
            assert.verifySteps(["on_attach_callback", "on_attach_callback"]);

            kanban.on_detach_callback();

            assert.verifySteps(["on_detach_callback", "on_detach_callback"]);

            kanban.destroy();
            testUtils.mock.unpatch(JournalDashboardGraph);
            done();
        });
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

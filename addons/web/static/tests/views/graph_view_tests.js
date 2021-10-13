/** @odoo-module **/

import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent } from "@web/../tests/helpers/utils";
import {
    editFavoriteName,
    saveFavorite,
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
    switchView,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
} from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { BORDER_WHITE, DEFAULT_BG } from "@web/views/graph/colors";
import { GraphArchParser } from "@web/views/graph/graph_arch_parser";
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "../helpers/utils";

const serviceRegistry = registry.category("services");

function getGraphModelMetaData(graph) {
    return graph.model.metaData;
}

export function getGraphRenderer(graph) {
    const layout = Object.values(graph.__owl__.children)[0];
    return Object.values(layout.__owl__.children).find((c) => c.chart);
}

function getChart(graph) {
    return getGraphRenderer(graph).chart;
}

function checkDatasets(assert, graph, keys, expectedDatasets) {
    keys = keys instanceof Array ? keys : [keys];
    expectedDatasets = expectedDatasets instanceof Array ? expectedDatasets : [expectedDatasets];
    const datasets = getChart(graph).data.datasets;
    const actualValues = [];
    for (const dataset of datasets) {
        const partialDataset = {};
        for (const key of keys) {
            partialDataset[key] = dataset[key];
        }
        actualValues.push(partialDataset);
    }
    assert.deepEqual(actualValues, expectedDatasets);
}

function checkLabels(assert, graph, expectedLabels) {
    const labels = getChart(graph).data.labels.map((l) => l.toString());
    assert.deepEqual(labels, expectedLabels);
}

function checkLegend(assert, graph, expectedLegendLabels) {
    expectedLegendLabels =
        expectedLegendLabels instanceof Array ? expectedLegendLabels : [expectedLegendLabels];
    const chart = getChart(graph);
    const actualLegendLabels = chart.config.options.legend.labels
        .generateLabels(chart)
        .map((o) => o.text);
    assert.deepEqual(actualLegendLabels, expectedLegendLabels);
}

function checkTooltip(assert, graph, expectedTooltipContent, index, datasetIndex) {
    // If the tooltip options are changed, this helper should change: we construct the dataPoints
    // similarly to Chart.js according to the values set for the tooltips options 'mode' and 'intersect'.
    const { datasets } = getChart(graph).data;
    const dataPoints = [];
    for (let i = 0; i < datasets.length; i++) {
        const dataset = datasets[i];
        const yLabel = dataset.data[index];
        if (yLabel !== undefined && (datasetIndex === undefined || datasetIndex === i)) {
            dataPoints.push({
                datasetIndex: i,
                index,
                yLabel,
            });
        }
    }
    const tooltipModel = { opacity: 1, x: 1, y: 1, dataPoints };
    getChart(graph).config.options.tooltips.custom(tooltipModel);
    const { title, lines } = expectedTooltipContent;
    const lineLabels = [];
    const lineValues = [];
    for (const line of lines) {
        lineLabels.push(line.label);
        lineValues.push(`${line.value}`);
    }
    assert.containsOnce(graph, "div.o_graph_custom_tooltip");
    const tooltipTitle = graph.el.querySelector("table thead tr th.o_measure");
    assert.strictEqual(tooltipTitle.innerText, title || "Count", `Tooltip title`);
    assert.deepEqual(
        [...graph.el.querySelectorAll("table tbody tr td span.o_label")].map((td) => td.innerText),
        lineLabels,
        `Tooltip line labels`
    );
    assert.deepEqual(
        [...graph.el.querySelectorAll("table tbody tr td.o_value")].map((td) => td.innerText),
        lineValues,
        `Tooltip line values`
    );
}

function getModeButton(comp, mode) {
    return comp.el.querySelector(`.o_graph_button[data-mode="${mode}"`);
}

async function selectMode(comp, mode) {
    await click(getModeButton(comp, mode));
}

function checkModeIs(assert, graph, mode) {
    assert.strictEqual(getGraphModelMetaData(graph).mode, mode);
    assert.strictEqual(getChart(graph).config.type, mode);
    assert.hasClass(getModeButton(graph, mode), "active");
}

function getXAxeLabel(graph) {
    return getChart(graph).config.options.scales.xAxes[0].scaleLabel.labelString;
}

function getYAxeLabel(graph) {
    return getChart(graph).config.options.scales.yAxes[0].scaleLabel.labelString;
}

async function clickOnDataset(graph) {
    const chart = getChart(graph);
    const meta = chart.getDatasetMeta(0);
    const rectangle = chart.canvas.getBoundingClientRect();
    const point = meta.data[0].getCenterPoint();
    await triggerEvent(chart.canvas, null, "click", {
        pageX: rectangle.left + point.x,
        pageY: rectangle.top + point.y,
    });
}

let serverData;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        id: { string: "Id", type: "integer" },
                        foo: { string: "Foo", type: "integer", store: true, group_operator: "sum" },
                        bar: { string: "bar", type: "boolean", store: true },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            store: true,
                        },
                        color_id: {
                            string: "Color",
                            type: "many2one",
                            relation: "color",
                            store: true,
                        },
                        date: { string: "Date", type: "date", store: true, sortable: true },
                        revenue: {
                            string: "Revenue",
                            type: "float",
                            store: true,
                            group_operator: "sum",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: 3,
                            bar: true,
                            product_id: 37,
                            date: "2016-01-01",
                            revenue: 1,
                        },
                        {
                            id: 2,
                            foo: 53,
                            bar: true,
                            product_id: 37,
                            color_id: 7,
                            date: "2016-01-03",
                            revenue: 2,
                        },
                        {
                            id: 3,
                            foo: 2,
                            bar: true,
                            product_id: 37,
                            date: "2016-03-04",
                            revenue: 3,
                        },
                        {
                            id: 4,
                            foo: 24,
                            bar: false,
                            product_id: 37,
                            date: "2016-03-07",
                            revenue: 4,
                        },
                        {
                            id: 5,
                            foo: 4,
                            bar: false,
                            product_id: 41,
                            date: "2016-05-01",
                            revenue: 5,
                        },
                        { id: 6, foo: 63, bar: false, product_id: 41 },
                        { id: 7, foo: 42, bar: false, product_id: 41 },
                        {
                            id: 8,
                            foo: 48,
                            bar: false,
                            product_id: 41,
                            date: "2016-04-01",
                            revenue: 8,
                        },
                    ],
                },
                product: {
                    fields: {
                        id: { string: "Id", type: "integer" },
                        name: { string: "Product Name", type: "char" },
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
                color: {
                    fields: {
                        id: { string: "Id", type: "integer" },
                        name: { string: "Color", type: "char" },
                    },
                    records: [
                        {
                            id: 7,
                            display_name: "red",
                        },
                        {
                            id: 14,
                            display_name: "black",
                        },
                    ],
                },
            },
            views: {
                "foo,false,graph": `<graph/>`,
                "foo,false,search": `
                    <search>
                        <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                        <filter name="filter_with_context"
                            string="Filter With Context"
                            domain="[]"
                            context="{ 'graph_measure': 'foo', 'graph_mode': 'line', 'graph_groupbys': ['color_id'] }"
                            />
                        <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }"/>
                        <filter name="group_by_product" string="Product" context="{ 'group_by': 'product_id' }"/>
                    </search>
                `,
            },
        };
        setupControlPanelServiceRegistry();
        setupControlPanelFavoriteMenuRegistry();
        serviceRegistry.add("dialog", dialogService);
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
    });

    QUnit.module("GraphView");

    QUnit.test("simple bar chart rendering", async function (assert) {
        assert.expect(12);
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        const { measure, mode, order, stacked } = getGraphModelMetaData(graph);
        assert.containsOnce(graph, "div.o_graph_canvas_container canvas");
        assert.strictEqual(measure, "__count", `the active measure should be "__count" by default`);
        assert.strictEqual(mode, "bar", "should be in bar chart mode by default");
        assert.strictEqual(order, null, "should not be ordered by default");
        assert.strictEqual(stacked, true, "bar charts should be stacked by default");
        checkLabels(assert, graph, ["Total"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label", "stack"], {
            backgroundColor: "#1f77b4",
            borderColor: undefined,
            data: [8],
            label: "Count",
            stack: "",
        });
        checkLegend(assert, graph, "Count");
        checkTooltip(assert, graph, { lines: [{ label: "Total", value: "8" }] }, 0);
    });

    QUnit.test("simple bar chart rendering with no data", async function (assert) {
        assert.expect(4);
        serverData.models.foo.records = [];
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        assert.containsOnce(graph, "div.o_graph_canvas_container canvas");
        assert.containsNone(graph, ".o_nocontent_help");
        checkLabels(assert, graph, []);
        checkDatasets(assert, graph, [], []);
    });

    QUnit.test("simple bar chart rendering (one groupBy)", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph><field name="bar"/></graph>`,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["true", "false"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "#1f77b4",
            borderColor: undefined,
            data: [3, 5],
            label: "Count",
        });
        checkLegend(assert, graph, "Count");
        checkTooltip(assert, graph, { lines: [{ label: "true", value: "3" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "false", value: "5" }] }, 1);
    });

    QUnit.test("simple bar chart rendering (two groupBy)", async function (assert) {
        assert.expect(20);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="bar"/>
                    <field name="product_id"/>
                </graph>
            `,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["true", "false"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: "#1f77b4",
                    borderColor: undefined,
                    data: [3, 1],
                    label: "xphone",
                },
                {
                    backgroundColor: "#ff7f0e",
                    borderColor: undefined,
                    data: [0, 4],
                    label: "xpad",
                },
            ]
        );
        checkLegend(assert, graph, ["xphone", "xpad"]);
        checkTooltip(assert, graph, { lines: [{ label: "true / xphone", value: "3" }] }, 0, 0);
        checkTooltip(assert, graph, { lines: [{ label: "false / xphone", value: "1" }] }, 1, 0);
        checkTooltip(assert, graph, { lines: [{ label: "true / xpad", value: "0" }] }, 0, 1);
        checkTooltip(assert, graph, { lines: [{ label: "false / xpad", value: "4" }] }, 1, 1);
    });

    QUnit.test("bar chart rendering (no groupBy, several domains)", async function (assert) {
        assert.expect(11);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="revenue" type="measure"/>
                </graph>
            `,
            groupBy: [],
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["Total"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: "#1f77b4",
                    borderColor: undefined,
                    data: [6],
                    label: "True group",
                },
                {
                    backgroundColor: "#ff7f0e",
                    borderColor: undefined,
                    data: [17],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["True group", "False group"]);
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "Total / True group", value: "6" }],
            },
            0,
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "Total / False group", value: "17" }],
            },
            0,
            1
        );
    });

    QUnit.test("bar chart rendering (one groupBy, several domains)", async function (assert) {
        assert.expect(19);
        serverData.models.foo.records = [
            { bar: true, foo: 1, revenue: 14 },
            { bar: true, foo: 2, revenue: false },
            { bar: false, foo: 1, revenue: 12 },
            { bar: false, foo: 2, revenue: -4 },
            { bar: false, foo: 3, revenue: 2 },
            { bar: false, foo: 4, revenue: 0 },
        ];
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="revenue" type="measure"/>
                    <field name="foo"/>
                </graph>
            `,
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["1", "2", "3", "4"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: "#1f77b4",
                    borderColor: undefined,
                    data: [14, 0, 0, 0],
                    label: "True group",
                },
                {
                    backgroundColor: "#ff7f0e",
                    borderColor: undefined,
                    data: [12, -4, 2, 0],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["True group", "False group"]);
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "1 / True group", value: "14" }],
            },
            0,
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "1 / False group", value: "12" }],
            },
            0,
            1
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "2 / False group", value: "-4" }],
            },
            1,
            1
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "3 / False group", value: "2" }],
            },
            2,
            1
        );
    });

    QUnit.test(
        "bar chart rendering (one groupBy, several domains with date identification)",
        async function (assert) {
            assert.expect(23);
            serverData.models.foo.records = [
                { date: "2021-01-04", revenue: 12 },
                { date: "2021-01-12", revenue: 5 },
                { date: "2021-01-19", revenue: 15 },
                { date: "2021-01-26", revenue: 2 },
                { date: "2021-02-04", revenue: 14 },
                { date: "2021-02-17", revenue: false },
                { date: false, revenue: 0 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="revenue" type="measure"/>
                        <field name="date" interval="week"/>
                    </graph>
                `,
                comparison: {
                    domains: [
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-02-01"],
                                ["date", "<=", "2021-02-28"],
                            ],
                            description: "February 2021",
                        },
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-01-01"],
                                ["date", "<=", "2021-01-31"],
                            ],
                            description: "January 2021",
                        },
                    ],
                    fieldName: "date",
                },
            });
            checkLabels(assert, graph, ["W05 2021", "W07 2021", "", ""]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: "#1f77b4",
                        borderColor: undefined,
                        data: [14, 0],
                        label: "February 2021",
                    },
                    {
                        backgroundColor: "#ff7f0e",
                        borderColor: undefined,
                        data: [12, 5, 15, 2],
                        label: "January 2021",
                    },
                ]
            );
            checkLegend(assert, graph, ["February 2021", "January 2021"]);
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W05 2021 / February 2021", value: "14" }],
                },
                0,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W01 2021 / January 2021", value: "12" }],
                },
                0,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W02 2021 / January 2021", value: "5" }],
                },
                1,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W03 2021 / January 2021", value: "15" }],
                },
                2,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W04 2021 / January 2021", value: "2" }],
                },
                3,
                1
            );
        }
    );

    QUnit.test(
        "bar chart rendering (two groupBy, several domains with no date identification)",
        async function (assert) {
            assert.expect(15);
            serverData.models.foo.records = [
                { date: "2021-01-04", bar: true, revenue: 12 },
                { date: "2021-01-12", bar: false, revenue: 5 },
                { date: "2021-02-04", bar: true, revenue: 14 },
                { date: "2021-02-17", bar: false, revenue: false },
                { date: false, bar: true, revenue: 0 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="revenue" type="measure"/>
                        <field name="bar"/>
                        <field name="date" interval="week"/>
                    </graph>
                `,
                comparison: {
                    domains: [
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-02-01"],
                                ["date", "<=", "2021-02-28"],
                            ],
                            description: "February 2021",
                        },
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-01-01"],
                                ["date", "<=", "2021-01-31"],
                            ],
                            description: "January 2021",
                        },
                    ],
                    fieldName: "date",
                },
            });
            checkLabels(assert, graph, ["true", "false"]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: "#1f77b4",
                        borderColor: undefined,
                        data: [14, 0],
                        label: "February 2021 / W05 2021",
                    },
                    {
                        backgroundColor: "#ff7f0e",
                        borderColor: undefined,
                        data: [0, 0],
                        label: "February 2021 / W07 2021",
                    },
                    {
                        backgroundColor: "#aec7e8",
                        borderColor: undefined,
                        data: [12, 0],
                        label: "January 2021 / W01 2021",
                    },
                    {
                        backgroundColor: "#ffbb78",
                        borderColor: undefined,
                        data: [0, 5],
                        label: "January 2021 / W02 2021",
                    },
                ]
            );
            checkLegend(assert, graph, [
                "February 2021 / W05 2021",
                "February 2021 / W07 2021",
                "January 2021 / W01 2021",
                "January 2021 / W02 2021",
            ]);
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "true / February 2021 / W05 2021", value: "14" }],
                },
                0,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "true / January 2021 / W01 2021", value: "12" }],
                },
                0,
                2
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "false / January 2021 / W02 2021", value: "5" }],
                },
                1,
                3
            );
        }
    );

    QUnit.test("line chart rendering (no groupBy)", async function (assert) {
        assert.expect(9);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="line"/>`,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        const { mode } = getGraphModelMetaData(graph);
        assert.strictEqual(mode, "line");
        checkLabels(assert, graph, ["", "Total", ""]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label", "stack"], {
            backgroundColor: "rgba(31,119,180,0.4)",
            borderColor: "#1f77b4",
            data: [undefined, 8],
            label: "Count",
            stack: undefined,
        });
        checkLegend(assert, graph, "Count");
        checkTooltip(assert, graph, { lines: [{ label: "Total", value: "8" }] }, 1);
    });

    QUnit.test("line chart rendering (one groupBy)", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line">
                    <field name="bar"/>
                </graph>
            `,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["true", "false"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "rgba(31,119,180,0.4)",
            borderColor: "#1f77b4",
            data: [3, 5],
            label: "Count",
        });
        checkLegend(assert, graph, "Count");
        checkTooltip(assert, graph, { lines: [{ label: "true", value: "3" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "false", value: "5" }] }, 1);
    });

    QUnit.test("line chart rendering (two groupBy)", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line">
                    <field name="bar"/>
                    <field name="product_id"/>
                </graph>
            `,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["true", "false"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: undefined,
                    borderColor: "#1f77b4",
                    data: [3, 1],
                    label: "xphone",
                },
                {
                    backgroundColor: undefined,
                    borderColor: "#ff7f0e",
                    data: [0, 4],
                    label: "xpad",
                },
            ]
        );
        checkLegend(assert, graph, ["xphone", "xpad"]);
        checkTooltip(
            assert,
            graph,
            {
                lines: [
                    { label: "true / xphone", value: "3" },
                    { label: "true / xpad", value: "0" },
                ],
            },
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                lines: [
                    { label: "false / xpad", value: "4" },
                    { label: "false / xphone", value: "1" },
                ],
            },
            1
        );
    });

    QUnit.test("line chart rendering (no groupBy, several domains)", async function (assert) {
        assert.expect(7);
        const graph = await makeView({
            serverData,
            resModel: "foo",
            type: "graph",
            arch: `
                <graph type="line">
                    <field name="revenue" type="measure"/>
                </graph>
            `,
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["", "Total", ""]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: "rgba(31,119,180,0.4)",
                    borderColor: "#1f77b4",
                    data: [undefined, 6],
                    label: "True group",
                },
                {
                    backgroundColor: undefined,
                    borderColor: "#ff7f0e",
                    data: [undefined, 17],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["True group", "False group"]);
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [
                    { label: "Total / False group", value: "17" },
                    { label: "Total / True group", value: "6" },
                ],
            },
            1
        );
    });

    QUnit.test("line chart rendering (one groupBy, several domains)", async function (assert) {
        assert.expect(19);
        serverData.models.foo.records = [
            { bar: true, foo: 1, revenue: 14 },
            { bar: true, foo: 2, revenue: false },
            { bar: false, foo: 1, revenue: 12 },
            { bar: false, foo: 2, revenue: -4 },
            { bar: false, foo: 3, revenue: 2 },
            { bar: false, foo: 4, revenue: 0 },
        ];
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line">
                    <field name="revenue" type="measure"/>
                    <field name="foo"/>
                </graph>
            `,
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["1", "2", "3", "4"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: "rgba(31,119,180,0.4)",
                    borderColor: "#1f77b4",
                    data: [14, 0, 0, 0],
                    label: "True group",
                },
                {
                    backgroundColor: undefined,
                    borderColor: "#ff7f0e",
                    data: [12, -4, 2, 0],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["True group", "False group"]);
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [
                    { label: "1 / True group", value: "14" },
                    { label: "1 / False group", value: "12" },
                ],
            },
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [
                    { label: "2 / True group", value: "0" },
                    { label: "2 / False group", value: "-4" },
                ],
            },
            1
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [
                    { label: "3 / False group", value: "2" },
                    { label: "3 / True group", value: "0" },
                ],
            },
            2
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [
                    { label: "4 / True group", value: "0" },
                    { label: "4 / False group", value: "0" },
                ],
            },
            3
        );
    });

    QUnit.test(
        "line chart rendering (one groupBy, several domains with date identification)",
        async function (assert) {
            assert.expect(19);
            serverData.models.foo.records = [
                { date: "2021-01-04", revenue: 12 },
                { date: "2021-01-12", revenue: 5 },
                { date: "2021-01-19", revenue: 15 },
                { date: "2021-01-26", revenue: 2 },
                { date: "2021-02-04", revenue: 14 },
                { date: "2021-02-17", revenue: false },
                { date: false, revenue: 0 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line">
                        <field name="revenue" type="measure"/>
                        <field name="date" interval="week"/>
                    </graph>
                `,
                comparison: {
                    domains: [
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-02-01"],
                                ["date", "<=", "2021-02-28"],
                            ],
                            description: "February 2021",
                        },
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-01-01"],
                                ["date", "<=", "2021-01-31"],
                            ],
                            description: "January 2021",
                        },
                    ],
                    fieldName: "date",
                },
            });
            checkLabels(assert, graph, ["W05 2021", "W07 2021", "", ""]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: "rgba(31,119,180,0.4)",
                        borderColor: "#1f77b4",
                        data: [14, 0],
                        label: "February 2021",
                    },
                    {
                        backgroundColor: undefined,
                        borderColor: "#ff7f0e",
                        data: [12, 5, 15, 2],
                        label: "January 2021",
                    },
                ]
            );
            checkLegend(assert, graph, ["February 2021", "January 2021"]);
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [
                        { label: "W05 2021 / February 2021", value: "14" },
                        { label: "W01 2021 / January 2021", value: "12" },
                    ],
                },
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [
                        { label: "W02 2021 / January 2021", value: "5" },
                        { label: "W07 2021 / February 2021", value: "0" },
                    ],
                },
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W03 2021 / January 2021", value: "15" }],
                },
                2
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "W04 2021 / January 2021", value: "2" }],
                },
                3
            );
        }
    );

    QUnit.test(
        "line chart rendering (two groupBy, several domains with no date identification)",
        async function (assert) {
            assert.expect(11);
            serverData.models.foo.records = [
                { date: "2021-01-04", bar: true, revenue: 12 },
                { date: "2021-01-12", bar: false, revenue: 5 },
                { date: "2021-02-04", bar: true, revenue: 14 },
                { date: "2021-02-17", bar: false, revenue: false },
                { date: false, bar: true, revenue: 0 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line">
                        <field name="revenue" type="measure"/>
                        <field name="bar"/>
                        <field name="date" interval="week"/>
                    </graph>
                `,
                comparison: {
                    domains: [
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-02-01"],
                                ["date", "<=", "2021-02-28"],
                            ],
                            description: "February 2021",
                        },
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-01-01"],
                                ["date", "<=", "2021-01-31"],
                            ],
                            description: "January 2021",
                        },
                    ],
                    fieldName: "date",
                },
            });
            checkLabels(assert, graph, ["true", "false"]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: undefined,
                        borderColor: "#1f77b4",
                        data: [14, 0],
                        label: "February 2021 / W05 2021",
                    },
                    {
                        backgroundColor: undefined,
                        borderColor: "#ff7f0e",
                        data: [0, 0],
                        label: "February 2021 / W07 2021",
                    },
                    {
                        backgroundColor: undefined,
                        borderColor: "#aec7e8",
                        data: [12, 0],
                        label: "January 2021 / W01 2021",
                    },
                    {
                        backgroundColor: undefined,
                        borderColor: "#ffbb78",
                        data: [0, 5],
                        label: "January 2021 / W02 2021",
                    },
                ]
            );
            checkLegend(assert, graph, [
                "February 2021 / W05 2021",
                "February 2021 / W07 2021",
                "January 2021 / W01 2021",
                "January 2021 / W02 2021",
            ]);
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [
                        { label: "true / February 2021 / W05 2021", value: "14" },
                        { label: "true / January 2021 / W01 2021", value: "12" },
                        { label: "true / February 2021 / W07 2021", value: "0" },
                        { label: "true / January 2021 / W02 2021", value: "0" },
                    ],
                },
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [
                        { label: "false / January 2021 / W02 2021", value: "5" },
                        { label: "false / February 2021 / W05 2021", value: "0" },
                        { label: "false / February 2021 / W07 2021", value: "0" },
                        { label: "false / January 2021 / W01 2021", value: "0" },
                    ],
                },
                1
            );
        }
    );

    QUnit.test("displaying line chart with only 1 data point", async function (assert) {
        assert.expect(1);
        // this test makes sure the line chart does not crash when only one data
        // point is displayed.
        serverData.models.foo.records = serverData.models.foo.records.slice(0, 1);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="line"/>`,
        });
        assert.containsOnce(graph, "canvas", "should have a canvas");
    });

    QUnit.test("pie chart rendering (no groupBy)", async function (assert) {
        assert.expect(9);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="pie"/>`,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        const { mode } = getGraphModelMetaData(graph);
        assert.strictEqual(mode, "pie");
        checkLabels(assert, graph, ["Total"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label", "stack"], {
            backgroundColor: ["#1f77b4"],
            borderColor: BORDER_WHITE,
            data: [8],
            label: "",
            stack: undefined,
        });
        checkLegend(assert, graph, "Total");
        checkTooltip(assert, graph, { lines: [{ label: "Total", value: "8 (100.00%)" }] }, 0);
    });

    QUnit.test("pie chart rendering (one groupBy)", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="pie">
                    <field name="bar"/>
                </graph>
            `,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["true", "false"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data"], {
            backgroundColor: ["#1f77b4", "#ff7f0e"],
            borderColor: BORDER_WHITE,
            data: [3, 5],
        });
        checkLegend(assert, graph, ["true", "false"]);
        checkTooltip(assert, graph, { lines: [{ label: "true", value: "3 (37.50%)" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "false", value: "5 (62.50%)" }] }, 1);
    });

    QUnit.test("pie chart rendering (two groupBy)", async function (assert) {
        assert.expect(16);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="pie">
                    <field name="bar"/>
                    <field name="product_id"/>
                </graph>
            `,
        });
        assert.containsOnce(graph.el, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["true / xphone", "false / xphone", "false / xpad"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
            borderColor: BORDER_WHITE,
            data: [3, 1, 4],
            label: "",
        });
        checkLegend(assert, graph, ["true / xphone", "false / xphone", "false / xpad"]);
        checkTooltip(assert, graph, { lines: [{ label: "true / xphone", value: "3 (37.50%)" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "false / xphone", value: "1 (12.50%)" }] }, 1);
        checkTooltip(assert, graph, { lines: [{ label: "false / xpad", value: "4 (50.00%)" }] }, 2);
    });

    QUnit.test("pie chart rendering (no groupBy, several domains)", async function (assert) {
        assert.expect(11);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="pie">
                    <field name="revenue" type="measure"/>
                </graph>
            `,
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["Total"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: ["#1f77b4"],
                    borderColor: BORDER_WHITE,
                    data: [6],
                    label: "True group",
                },
                {
                    backgroundColor: ["#1f77b4"],
                    borderColor: BORDER_WHITE,
                    data: [17],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["Total"]);
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "True group / Total", value: "6 (100.00%)" }],
            },
            0,
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "False group / Total", value: "17 (100.00%)" }],
            },
            0,
            1
        );
    });

    QUnit.test("pie chart rendering (one groupBy, several domains)", async function (assert) {
        assert.expect(19);
        serverData.models.foo.records = [
            { bar: true, foo: 1, revenue: 14 },
            { bar: true, foo: 2, revenue: false },
            { bar: false, foo: 1, revenue: 12 },
            { bar: false, foo: 2, revenue: 5 },
            { bar: false, foo: 3, revenue: 0 },
            { bar: false, foo: 4, revenue: 2 },
        ];
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="pie">
                    <field name="revenue" type="measure"/>
                    <field name="foo"/>
                </graph>
            `,
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["1", "2", "4"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                    borderColor: BORDER_WHITE,
                    data: [14, 0, 0],
                    label: "True group",
                },
                {
                    backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                    borderColor: BORDER_WHITE,
                    data: [12, 5, 2],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["1", "2", "4"]);
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "True group / 1", value: "14 (100.00%)" }],
            },
            0,
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "False group / 1", value: "12 (63.16%)" }],
            },
            0,
            1
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "False group / 2", value: "5 (26.32%)" }],
            },
            1,
            1
        );
        checkTooltip(
            assert,
            graph,
            {
                title: "Revenue",
                lines: [{ label: "False group / 4", value: "2 (10.53%)" }],
            },
            2,
            1
        );
    });

    QUnit.test(
        "pie chart rendering (one groupBy, several domains with date identification)",
        async function (assert) {
            assert.expect(27);
            serverData.models.foo.records = [
                { date: "2021-01-04" },
                { date: "2021-01-12" },
                { date: "2021-01-19" },
                { date: "2021-01-26" },
                { date: "2021-02-04" },
                { date: "2021-02-17" },
                { date: false },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="pie">
                        <field name="date" interval="week"/>
                    </graph>
                `,
                comparison: {
                    domains: [
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-02-01"],
                                ["date", "<=", "2021-02-28"],
                            ],
                            description: "February 2021",
                        },
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-01-01"],
                                ["date", "<=", "2021-01-31"],
                            ],
                            description: "January 2021",
                        },
                    ],
                    fieldName: "date",
                },
            });
            checkLabels(assert, graph, [
                "W05 2021, W01 2021",
                "W07 2021, W02 2021",
                "W03 2021",
                "W04 2021",
            ]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8", "#ffbb78"],
                        borderColor: BORDER_WHITE,
                        data: [1, 1, 0, 0],
                        label: "February 2021",
                    },
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8", "#ffbb78"],
                        borderColor: BORDER_WHITE,
                        data: [1, 1, 1, 1],
                        label: "January 2021",
                    },
                ]
            );
            checkLegend(assert, graph, [
                "W05 2021, W01 2021",
                "W07 2021, W02 2021",
                "W03 2021",
                "W04 2021",
            ]);
            checkTooltip(
                assert,
                graph,
                {
                    lines: [{ label: "February 2021 / W05 2021", value: "1 (50.00%)" }],
                },
                0,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    lines: [{ label: "January 2021 / W01 2021", value: "1 (25.00%)" }],
                },
                0,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    lines: [{ label: "February 2021 / W07 2021", value: "1 (50.00%)" }],
                },
                1,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    lines: [{ label: "January 2021 / W02 2021", value: "1 (25.00%)" }],
                },
                1,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    lines: [{ label: "January 2021 / W03 2021", value: "1 (25.00%)" }],
                },
                2,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    lines: [{ label: "January 2021 / W04 2021", value: "1 (25.00%)" }],
                },
                3,
                1
            );
        }
    );

    QUnit.test(
        "pie chart rendering (two groupBy, several domains with no date identification)",
        async function (assert) {
            assert.expect(15);
            serverData.models.foo.records = [
                { date: "2021-01-04", bar: true, revenue: 12 },
                { date: "2021-01-12", bar: false, revenue: 5 },
                { date: "2021-02-04", bar: true, revenue: 14 },
                { date: "2021-02-17", bar: false, revenue: false },
                { date: false, bar: true, revenue: 0 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="pie">
                        <field name="revenue" type="measure"/>
                        <field name="bar"/>
                        <field name="date" interval="week"/>
                    </graph>
                `,
                comparison: {
                    domains: [
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-02-01"],
                                ["date", "<=", "2021-02-28"],
                            ],
                            description: "February 2021",
                        },
                        {
                            arrayRepr: [
                                ["date", ">=", "2021-01-01"],
                                ["date", "<=", "2021-01-31"],
                            ],
                            description: "January 2021",
                        },
                    ],
                    fieldName: "date",
                },
            });
            checkLabels(assert, graph, ["true / W05 2021", "true / W01 2021", "false / W02 2021"]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                        borderColor: BORDER_WHITE,
                        data: [14, 0, 0],
                        label: "February 2021",
                    },
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                        borderColor: BORDER_WHITE,
                        data: [0, 12, 5],
                        label: "January 2021",
                    },
                ]
            );
            checkLegend(assert, graph, ["true / W05 2021", "true / W01 2021", "false / W02 2021"]);
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "February 2021 / true / W05 2021", value: "14 (100.00%)" }],
                },
                0,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "January 2021 / true / W01 2021", value: "12 (70.59%)" }],
                },
                1,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "January 2021 / false / W02 2021", value: "5 (29.41%)" }],
                },
                2,
                1
            );
        }
    );

    QUnit.test("pie chart rendering (no data)", async function (assert) {
        assert.expect(7);
        serverData.models.foo.records = [];
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="pie"/>`,
        });
        checkLabels(assert, graph, ["No data"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: [DEFAULT_BG],
                    borderColor: BORDER_WHITE,
                    data: [1],
                    label: null,
                },
            ]
        );
        checkLegend(assert, graph, ["No data"]);
        checkTooltip(assert, graph, { lines: [{ label: "No data", value: "0 (100.00%)" }] }, 0);
    });

    QUnit.test("pie chart rendering (no data, several domains)", async function (assert) {
        assert.expect(11);
        serverData.models.foo.records = [{ product_id: 37, bar: true }];
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="pie">
                    <field name="product_id"/>
                </graph>
            `,
            comparison: {
                domains: [
                    { arrayRepr: [["bar", "=", true]], description: "True group" },
                    { arrayRepr: [["bar", "=", false]], description: "False group" },
                ],
            },
        });
        checkLabels(assert, graph, ["xphone", "No data"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: ["#1f77b4"],
                    borderColor: BORDER_WHITE,
                    data: [1],
                    label: "True group",
                },
                {
                    backgroundColor: ["#1f77b4", DEFAULT_BG],
                    borderColor: BORDER_WHITE,
                    data: [undefined, 1],
                    label: "False group",
                },
            ]
        );
        checkLegend(assert, graph, ["xphone", "No data"]);
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "True group / xphone", value: "1 (100.00%)" }] },
            0,
            0
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "False group / No data", value: "0 (100.00%)" }] },
            1,
            1
        );
    });

    QUnit.test(
        "pie chart rendering (mix of positive and negative values)",
        async function (assert) {
            assert.expect(3);
            serverData.models.foo.records = [
                { bar: true, revenue: 2 },
                { bar: false, revenue: -3 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="pie">
                        <field name="revenue" type="measure"/>
                        <field name="bar"/>
                    </graph>
                `,
            });
            assert.containsOnce(graph, ".o_view_nocontent");
            assert.strictEqual(
                graph.el.querySelector(".o_view_nocontent").innerText.replace(/[\s\n]/g, " "),
                `Invalid data  Pie chart cannot mix positive and negative numbers. Try to change your domain to only display positive results`
            );
            assert.containsNone(graph, ".o_graph_canvas_container");
        }
    );

    QUnit.test("mode props", async function (assert) {
        assert.expect(2);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="pie"/>`,
        });
        assert.strictEqual(getGraphModelMetaData(graph).mode, "pie", "should be in pie chart mode");
        assert.strictEqual(getChart(graph).config.type, "pie");
    });

    QUnit.test("field id not in groupBy", async function (assert) {
        assert.expect(3);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="id"/>
                </graph>
            `,
        });
        checkLabels(assert, graph, ["Total"]);
        checkDatasets(assert, graph, ["backgroundColor", "data", "label", "originIndex", "stack"], {
            backgroundColor: "#1f77b4",
            data: [8],
            label: "Count",
            originIndex: 0,
            stack: "",
        });
        checkLegend(assert, graph, "Count");
    });

    QUnit.test("props modifications", async function (assert) {
        assert.expect(16);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="bar"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }"/>
                </search>
            `,
        });
        checkModeIs(assert, graph, "bar");
        assert.strictEqual(getXAxeLabel(graph), "bar");
        assert.strictEqual(getYAxeLabel(graph), "Count");
        await selectMode(graph, "line");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(getXAxeLabel(graph), "bar");
        await toggleMenu(graph, "Measures");
        await toggleMenuItem(graph, "Revenue");
        assert.strictEqual(getYAxeLabel(graph), "Revenue");
        assert.ok(true, "Message");
        await toggleGroupByMenu(graph);
        await toggleMenuItem(graph, "Color");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(getXAxeLabel(graph), "Color");
        assert.strictEqual(getYAxeLabel(graph), "Revenue");
    });

    QUnit.test("switching mode", async function (assert) {
        assert.expect(12);
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        checkModeIs(assert, graph, "bar");
        await selectMode(graph, "bar"); // click on the active mode does not change anything
        checkModeIs(assert, graph, "bar");
        await selectMode(graph, "line");
        checkModeIs(assert, graph, "line");
        await selectMode(graph, "pie");
        checkModeIs(assert, graph, "pie");
    });

    QUnit.test("switching measure", async function (assert) {
        assert.expect(6);
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        function checkMeasure(measure) {
            const yAxe = getChart(graph).config.options.scales.yAxes[0];
            assert.strictEqual(yAxe.scaleLabel.labelString, measure);
            const item = [...graph.el.querySelectorAll(".o_menu_item")].find(
                (el) => el.innerText === measure
            );
            assert.hasClass(item, "selected");
        }
        await toggleMenu(graph, "Measures");
        checkMeasure("Count");
        checkLegend(assert, graph, "Count");
        await toggleMenuItem(graph, "Foo");
        checkMeasure("Foo");
        checkLegend(assert, graph, "Foo");
    });

    QUnit.test("process default view description", async function (assert) {
        assert.expect(1);
        const propsFromArch = new GraphArchParser().parse();
        assert.deepEqual(propsFromArch, { fields: {}, fieldAttrs: {}, groupBy: [] });
    });

    QUnit.test("process simple arch (no field tag)", async function (assert) {
        assert.expect(2);
        const fields = serverData.models.foo.fields;
        const arch1 = `<graph order="ASC" disable_linking="1" type="line"/>`;
        let propsFromArch = new GraphArchParser().parse(arch1, fields);

        assert.deepEqual(propsFromArch, {
            disableLinking: true,
            fields,
            fieldAttrs: {},
            groupBy: [],
            mode: "line",
            order: "ASC",
        });
        let arch2 = `<graph disable_linking="0" string="Title" stacked="False"/>`;
        propsFromArch = new GraphArchParser().parse(arch2, fields);

        assert.deepEqual(propsFromArch, {
            disableLinking: false,
            fields,
            fieldAttrs: {},
            groupBy: [],
            stacked: false,
            title: "Title",
        });
    });

    QUnit.test("process arch with field tags", async function (assert) {
        assert.expect(1);
        const fields = serverData.models.foo.fields;
        fields.fighters = { type: "text", string: "Fighters" };
        let arch = `
            <graph type="pie">
                <field name="revenue" type="measure"/>
                <field name="date" interval="day"/>
                <field name="foo" invisible="0"/>
                <field name="bar" invisible="1" string="My invisible field"/>
                <field name="id"/>
                <field name="fighters" string="FooFighters"/>
            </graph>
        `;
        let propsFromArch = new GraphArchParser().parse(arch, fields);
        assert.deepEqual(propsFromArch, {
            fields,
            fieldAttrs: {
                bar: { isInvisible: true, string: "My invisible field" },
                fighters: { string: "FooFighters" },
            },
            measure: "revenue",
            groupBy: ["date:day", "foo"],
            mode: "pie",
        });
    });

    QUnit.test("displaying chart data with three groupbys", async function (assert) {
        // this test makes sure the line chart shows all data labels (X axis) when
        // it is grouped by several fields
        assert.expect(6);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="bar">
                    <field name="product_id"/>
                    <field name="bar"/>
                    <field name="color_id"/>
                </graph>
            `,
        });

        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkLegend(assert, graph, ["true / Undefined", "true / red", "false / Undefined"]);

        await selectMode(graph, "line");

        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkLegend(assert, graph, ["true / Undefined", "true / red", "false / Undefined"]);

        await selectMode(graph, "pie");

        checkLabels(assert, graph, [
            "xphone / true / Undefined",
            "xphone / true / red",
            "xphone / false / Undefined",
            "xpad / false / Undefined",
        ]);
        checkLegend(assert, graph, [
            "xphone / true / Undefined",
            "xphone / true / red",
            "xphone / false / Undefined",
            "xpad / false / Undefined",
        ]);
    });

    QUnit.test("no content helper", async function (assert) {
        assert.expect(3);
        serverData.models.foo.records = [];
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            noContentHelp: '<p class="abc">This helper should not be displayed in graph views</p>',
        });
        assert.containsOnce(graph, "div.o_graph_canvas_container canvas");
        assert.containsNone(graph, "div.o_view_nocontent");
        assert.containsNone(graph, ".abc");
    });

    QUnit.test("no content helper after update", async function (assert) {
        assert.expect(6);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            noContentHelp: '<p class="abc">This helper should not be displayed in graph views</p>',
            config: {
                views: [[false, "search"]],
            },
        });
        assert.containsOnce(graph, "div.o_graph_canvas_container canvas");
        assert.containsNone(graph, "div.o_view_nocontent");
        assert.containsNone(graph, ".abc");
        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "False Domain");
        assert.containsOnce(graph, "div.o_graph_canvas_container canvas");
        assert.containsNone(graph, "div.o_view_nocontent");
        assert.containsNone(graph, ".abc");
    });

    QUnit.test("can reload with other group by", async function (assert) {
        assert.expect(2);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }"/>
                </search>
            `,
        });
        checkLabels(assert, graph, ["xphone", "xpad"]);
        await toggleGroupByMenu(graph);
        await toggleMenuItem(graph, "Color");
        checkLabels(assert, graph, ["Undefined", "red"]);
    });

    QUnit.test("save params succeeds", async function (assert) {
        assert.expect(4);
        const expectedContexts = [
            {
                graph_mode: "bar",
                graph_measure: "__count",
                graph_groupbys: ["product_id"],
                group_by: [],
            },
            {
                graph_mode: "bar",
                graph_measure: "foo",
                graph_groupbys: ["product_id"],
                group_by: [],
            },
            {
                graph_mode: "line",
                graph_measure: "foo",
                graph_groupbys: ["product_id"],
                group_by: [],
            },
            {
                graph_mode: "line",
                graph_measure: "foo",
                graph_groupbys: ["product_id", "color_id"],
                group_by: ["product_id", "color_id"],
            },
        ];

        let serverId = 1;
        const graph = await makeView({
            mockRPC: function (_, args) {
                if (args.method === "create_or_replace") {
                    const favorite = args.args[0];
                    assert.deepEqual(favorite.context, expectedContexts.shift());
                    return serverId++;
                }
            },
            serverData,
            resModel: "foo",
            type: "graph",
            arch: `
                    <graph>
                        <field name="product_id"/>
                    </graph>
                `,
            searchViewId: false,
            searchViewArch: `
                <search>
                    <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                    <filter name="filter_with_context"
                        string="Filter With Context"
                        domain="[]"
                        context="{ 'graph_measure': 'foo', 'graph_mode': 'line', 'graph_groupbys': ['color_id'] }"
                        />
                    <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }"/>
                    <filter name="group_by_product" string="Product" context="{ 'group_by': 'product_id' }"/>
                </search>
            `,
        });

        await toggleFavoriteMenu(graph);
        await toggleSaveFavorite(graph);
        await editFavoriteName(graph, "First Favorite");
        await saveFavorite(graph);

        await toggleMenu(graph, "Measures");
        await toggleMenuItem(graph, "Foo");

        await toggleFavoriteMenu(graph);
        await toggleSaveFavorite(graph);
        await editFavoriteName(graph, "Second Favorite");
        await saveFavorite(graph);

        await selectMode(graph, "line");

        await toggleFavoriteMenu(graph);
        await toggleSaveFavorite(graph);
        await editFavoriteName(graph, "Third Favorite");
        await saveFavorite(graph);

        await toggleGroupByMenu(graph);
        await toggleMenuItem(graph, "Product");
        await toggleMenuItem(graph, "Color");

        await toggleFavoriteMenu(graph);
        await toggleSaveFavorite(graph);
        await editFavoriteName(graph, "Fourth Favorite");
        await saveFavorite(graph);
    });

    QUnit.test("correctly uses graph_ keys from the context", async function (assert) {
        assert.expect(8);
        const recs = serverData.models.foo.records;
        const lastOne = recs[recs.length - 1];
        lastOne.color_id = 14;
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: '<graph><field name="product_id"/></graph>',
            context: {
                graph_measure: "foo",
                graph_mode: "line",
                graph_groupbys: ["color_id"],
            },
        });
        checkLabels(assert, graph, ["red", "black"]);
        checkLegend(assert, graph, "Foo");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(getXAxeLabel(graph), "Color");
        assert.strictEqual(getYAxeLabel(graph), "Foo");
        const { mode } = getGraphModelMetaData(graph);
        assert.strictEqual(mode, "line");
    });

    QUnit.test("correctly use group_by key from the context", async function (assert) {
        assert.expect(8);
        const recs = serverData.models.foo.records;
        const lastOne = recs[recs.length - 1];
        lastOne.color_id = 14;
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="filter_with_context"
                        string="Filter With Context"
                        domain="[]"
                        context="{ 'graph_measure': 'foo', 'graph_mode': 'line', 'graph_groupbys': ['color_id'] }"
                        />
                </search>
            `,
            context: {
                search_default_filter_with_context: 1,
            },
        });
        checkLabels(assert, graph, ["red", "black"]);
        checkLegend(assert, graph, "Foo");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(getXAxeLabel(graph), "Color");
        assert.strictEqual(getYAxeLabel(graph), "Foo");
        const mode = getGraphModelMetaData(graph).mode;
        assert.strictEqual(mode, "line");
    });

    QUnit.test("an invisible field should not be used as groupBy", async function (assert) {
        assert.expect(1);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="foo" invisible="1"/>
                </graph>
            `,
        });
        checkLabels(assert, graph, ["Total"]);
    });

    QUnit.test(
        "format values as float in case at least one value is not an integer",
        async function (assert) {
            assert.expect(10);
            serverData.models.foo.records = [
                { id: 1, bar: true, revenue: 1.5 },
                { id: 2, bar: false, revenue: 2 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="revenue" type="measure"/>
                        <field name="bar"/>
                    </graph>
                `,
            });
            checkDatasets(assert, graph, "data", { data: [1.5, 2] });
            checkLabels(assert, graph, ["true", "false"]);
            checkTooltip(
                assert,
                graph,
                { title: "Revenue", lines: [{ label: "true", value: "1.50" }] },
                0
            );
            checkTooltip(
                assert,
                graph,
                { title: "Revenue", lines: [{ label: "false", value: "2.00" }] },
                1
            );
        }
    );

    QUnit.test(
        "the active measure description is the arch string attribute in priority",
        async function (assert) {
            assert.expect(8);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="revenue" type="measure" string="Nirvana"/>
                        <field name="foo" type="measure" string="FooFighters"/>
                    </graph>
                `,
            });
            checkTooltip(
                assert,
                graph,
                { title: "FooFighters", lines: [{ label: "Total", value: "239" }] },
                0
            );
            await toggleMenu(graph, "Measures");
            await toggleMenuItem(graph, "Nirvana");
            checkTooltip(
                assert,
                graph,
                { title: "Nirvana", lines: [{ label: "Total", value: "23" }] },
                0
            );
        }
    );

    QUnit.test("correctly uses graph_ keys from the context (at reload)", async function (assert) {
        assert.expect(10);

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: '<graph><field name="product_id"/></graph>',
            searchViewArch: `
                <search>
                    <filter name="context" domain="[]" string="Context" context="{ 'graph_measure': 'foo', 'graph_mode': 'line' }"/>
                </search>
            `,
        });
        checkLegend(assert, graph, "Count");
        assert.strictEqual(getYAxeLabel(graph), "Count");
        checkModeIs(assert, graph, "bar");
        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "Context");
        checkLegend(assert, graph, "Foo");
        assert.strictEqual(getYAxeLabel(graph), "Foo");
        checkModeIs(assert, graph, "line");
    });

    QUnit.test("reload graph with correct fields", async function (assert) {
        assert.expect(2);
        const graph = await makeView({
            serverData,
            mockRPC: function (_, args) {
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.fields, ["__count", "foo:sum"]);
                }
            },
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="foo" type="measure"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                </search>
            `,
        });
        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "False Domain");
    });

    QUnit.test("initial groupby is kept when reloading", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            mockRPC: function (_, args) {
                if (args.method === "web_read_group") {
                    assert.deepEqual(args.kwargs.groupby, ["product_id"]);
                }
            },
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id"/>
                    <field name="foo" type="measure"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                </search>
            `,
        });
        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkLegend(assert, graph, "Foo");
        checkDatasets(assert, graph, "data", { data: [82, 157] });
        assert.strictEqual(getXAxeLabel(graph), "Product");
        assert.strictEqual(getYAxeLabel(graph), "Foo");
        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "False Domain");
        checkLabels(assert, graph, []);
        checkLegend(assert, graph, []);
        checkDatasets(assert, graph, "data", []);
        assert.strictEqual(getXAxeLabel(graph), "Product");
        assert.strictEqual(getYAxeLabel(graph), "Foo");
    });

    QUnit.test(
        "use a many2one as a measure should work (without groupBy)",
        async function (assert) {
            assert.expect(5);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="product_id" type="measure"/>
                    </graph>
                `,
            });
            checkLabels(assert, graph, ["Total"]);
            checkLegend(assert, graph, "Product");
            checkDatasets(assert, graph, "data", { data: [2] });
            assert.strictEqual(getXAxeLabel(graph), "");
            assert.strictEqual(getYAxeLabel(graph), "Product");
        }
    );

    QUnit.test("use a many2one as a measure should work (with groupBy)", async function (assert) {
        assert.expect(3);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
              <graph>
                  <field name="bar"/>
                  <field name="product_id" type="measure"/>
              </graph>
            `,
        });
        checkLabels(assert, graph, ["true", "false"]);
        checkLegend(assert, graph, "Product");
        checkDatasets(assert, graph, "data", { data: [1, 2] });
    });

    QUnit.test("use a many2one as a measure and as a groupby should work", async function (assert) {
        assert.expect(5);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id" type="measure"/>
                    <field name="product_id"/>
                </graph>
            `,
        });
        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkLegend(assert, graph, "Product");
        checkDatasets(assert, graph, "data", { data: [1, 1] });
        assert.strictEqual(getXAxeLabel(graph), "Product");
        assert.strictEqual(getYAxeLabel(graph), "Product");
    });

    QUnit.test("differentiate many2one values with same label", async function (assert) {
        assert.expect(1);
        serverData.models.product.records.push({ id: 39, display_name: "xphone" });
        serverData.models.foo.records.push({ id: 18, product_id: 39 });
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id"/>
                </graph>
            `,
        });
        checkLabels(assert, graph, ["xphone", "xpad", "xphone (2)"]);
    });

    QUnit.test("not use a many2one as a measure by default", async function (assert) {
        assert.expect(1);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: "<graph/>",
        });
        await toggleMenu(graph, "Measures");
        assert.deepEqual(
            [...graph.el.querySelectorAll(".o_cp_bottom_left .o_menu_item")].map(
                (el) => el.innerText
            ),
            ["Foo", "Revenue", "Count"]
        );
    });

    QUnit.test(
        "graph view crash when moving from search view using Down key",
        async function (assert) {
            assert.expect(1);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `<graph/>`,
            });
            await triggerEvent(graph.el, ".o_searchview input", "keydown", { key: "ArrowDown" });
            assert.ok(true, "should not generate any error");
        }
    );

    QUnit.test(
        "graph measures should be alphabetically sorted (exception: 'Count' is last)",
        async function (assert) {
            assert.expect(1);
            serverData.models.foo.fields.bouh = {
                string: "Bouh",
                type: "integer",
                store: true,
                group_operator: "sum",
            };
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="foo" type="measure"/>
                        <field name="bouh" type="measure"/>
                    </graph>
                `,
            });
            await toggleMenu(graph, "Measures");
            assert.deepEqual(
                [...graph.el.querySelectorAll(".o_cp_bottom_left .o_menu_item")].map(
                    (el) => el.innerText
                ),
                ["Bouh", "Foo", "Revenue", "Count"]
            );
        }
    );

    QUnit.test("a many2one field can be added as measure in arch", async function (assert) {
        assert.expect(2);

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id" type="measure"/>
                </graph>
            `,
        });
        checkLegend(assert, graph, "Product");
        assert.strictEqual(getYAxeLabel(graph), "Product");
    });

    QUnit.test(
        "a many2one field can be added as measure in additionalMeasures",
        async function (assert) {
            assert.expect(2);

            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `<graph/>`,
                additionalMeasures: ["product_id"],
            });
            await toggleMenu(graph, "Measures");
            await toggleMenuItem(graph, "Product");
            checkLegend(assert, graph, "Product");
            assert.strictEqual(getYAxeLabel(graph), "Product");
        }
    );

    QUnit.test('graph view "graph_measure" field in context', async function (assert) {
        assert.expect(6);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: "<graph/>",
            context: {
                graph_measure: "product_id",
            },
        });
        checkLegend(assert, graph, "Product");
        assert.strictEqual(getYAxeLabel(graph), "Product");
        checkTooltip(
            assert,
            graph,
            { title: "Product", lines: [{ label: "Total", value: "2" }] },
            0
        );
    });

    QUnit.test(
        '"graph_measure" in context is prefered to measure in arch',
        async function (assert) {
            assert.expect(6);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: '<graph><field name="revenue" type="measure"/></graph>',
                context: {
                    graph_measure: "product_id",
                },
            });
            checkLegend(assert, graph, "Product");
            assert.strictEqual(getYAxeLabel(graph), "Product");
            checkTooltip(
                assert,
                graph,
                { title: "Product", lines: [{ label: "Total", value: "2" }] },
                0
            );
        }
    );

    QUnit.test(
        "Undefined should appear in bar, pie graph but not in line graph with multiple groupbys",
        async function (assert) {
            assert.expect(4);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line">
                        <field name="date"/>
                        <field name="color_id"/>
                    </graph>
                `,
            });
            function someUndefined() {
                return getChart(graph).data.labels.some((l) => /Undefined/.test(l));
            }
            assert.notOk(someUndefined());
            await selectMode(graph, "bar");
            assert.ok(someUndefined());
            await selectMode(graph, "pie");
            assert.ok(someUndefined());
            // Undefined should not appear after switching back to line chart
            await selectMode(graph, "line");
            assert.notOk(someUndefined());
        }
    );

    QUnit.test(
        "an invisible field in additional measure can be found in the 'Measures' menu",
        async function (assert) {
            assert.expect(8);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="revenue" invisible="1"/>
                    </graph>
                `,
                additionalMeasures: ["revenue"],
            });
            checkTooltip(assert, graph, { lines: [{ label: "Total", value: "8" }] }, 0);
            await toggleMenu(graph, "Measures");
            await toggleMenuItem(graph, "Revenue");
            checkTooltip(
                assert,
                graph,
                { title: "Revenue", lines: [{ label: "Total", value: "23" }] },
                0
            );
        }
    );

    QUnit.test(
        "an invisible field not in additional measure can not be found in the 'Measures' menu",
        async function (assert) {
            assert.expect(5);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph>
                        <field name="revenue" invisible="1"/>
                    </graph>
                `,
            });
            checkTooltip(assert, graph, { lines: [{ label: "Total", value: "8" }] }, 0);
            await toggleMenu(graph, "Measures");
            assert.notOk(
                [...graph.el.querySelectorAll(".o_menu_item")].find(
                    (el) => el.innerText.trim() === "Revenue"
                ),
                `"Revenue" can not be found in the "Measures" menu`
            );
        }
    );

    QUnit.test(
        "graph view only keeps finer groupby filter option for a given groupby",
        async function (assert) {
            assert.expect(3);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                groupBy: ["date:year", "product_id", "date", "date:quarter"],
                arch: `<graph type="line"/>`,
                config: {
                    views: [[false, "search"]],
                },
            });
            checkLabels(assert, graph, ["January 2016", "March 2016", "May 2016", "April 2016"]);
            // mockReadGroup does not always sort groups -> May 2016 is before April 2016 for that reason.
            checkLegend(assert, graph, ["xphone", "xpad"]);
            checkDatasets(
                assert,
                graph,
                ["label", "data"],
                [
                    {
                        label: "xphone",
                        data: [2, 2, 0, 0],
                    },
                    {
                        label: "xpad",
                        data: [0, 0, 1, 1],
                    },
                ]
            );
        }
    );

    QUnit.test("action name is displayed in breadcrumbs", async function (assert) {
        assert.expect(1);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            config: {
                displayName: "Glou glou",
            },
        });
        assert.strictEqual(
            graph.el.querySelector(".o_control_panel .breadcrumb-item.active").innerText,
            "Glou glou"
        );
    });

    QUnit.test("clicking on bar charts triggers a do_action", async function (assert) {
        assert.expect(6);

        serviceRegistry.add(
            "action",
            {
                start() {
                    return {
                        doAction(actionRequest, options) {
                            assert.deepEqual(actionRequest, {
                                context: {
                                    lang: "en",
                                    tz: "taht",
                                    uid: 7,
                                },
                                domain: [["bar", "=", true]],
                                name: "Foo Analysis",
                                res_model: "foo",
                                target: "current",
                                type: "ir.actions.act_window",
                                views: [
                                    [false, "list"],
                                    [false, "form"],
                                ],
                            });
                            assert.deepEqual(options, { viewType: "list" });
                        },
                    };
                },
            },
            { force: true }
        );
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph string="Foo Analysis">
                    <field name="bar"/>
                </graph>
            `,
        });
        checkModeIs(assert, graph, "bar");
        checkDatasets(assert, graph, ["domains"], {
            domains: [[["bar", "=", true]], [["bar", "=", false]]],
        });
        await clickOnDataset(graph);
    });

    QUnit.test(
        "clicking on a pie chart trigger a do_action with correct views",
        async function (assert) {
            assert.expect(6);
            serverData.views["foo,364,list"] = `<list/>`;
            serverData.views["foo,29,form"] = `<form/>`;

            serviceRegistry.add(
                "action",
                {
                    start() {
                        return {
                            doAction(actionRequest, options) {
                                assert.deepEqual(actionRequest, {
                                    context: {
                                        lang: "en",
                                        tz: "taht",
                                        uid: 7,
                                    },
                                    domain: [["bar", "=", true]],
                                    name: "Foo Analysis",
                                    res_model: "foo",
                                    target: "current",
                                    type: "ir.actions.act_window",
                                    views: [
                                        [364, "list"],
                                        [29, "form"],
                                    ],
                                });
                                assert.deepEqual(options, { viewType: "list" });
                            },
                        };
                    },
                },
                { force: true }
            );

            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph string="Foo Analysis" type="pie">
                        <field name="bar"/>
                    </graph>
                `,
                config: {
                    views: [
                        [364, "list"],
                        [29, "form"],
                    ],
                },
            });
            checkModeIs(assert, graph, "pie");
            checkDatasets(assert, graph, ["domains"], {
                domains: [[["bar", "=", true]], [["bar", "=", false]]],
            });
            await clickOnDataset(graph);
        }
    );

    QUnit.test('graph view with attribute disable_linking="1"', async function (assert) {
        assert.expect(4);

        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add(
            "action",
            {
                start() {
                    return {
                        doAction() {
                            throw new Error("Should not perform a do_action");
                        },
                    };
                },
            },
            { force: true }
        );

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph disable_linking="1">
                    <field name="bar"/>
                </graph>
            `,
        });
        checkModeIs(assert, graph, "bar");
        checkDatasets(assert, graph, ["domains"], {
            domains: [[["bar", "=", true]], [["bar", "=", false]]],
        });
        await clickOnDataset(graph);
    });

    QUnit.test("graph view without invisible attribute on field", async function (assert) {
        assert.expect(4);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph/>`,
        });
        await toggleMenu(graph, "Measures");
        assert.containsN(
            graph,
            ".o_menu_item",
            3,
            "there should be three menu item in the measures dropdown (count, revenue and foo)"
        );
        assert.containsOnce(graph, '.o_menu_item:contains("Revenue")');
        assert.containsOnce(graph, '.o_menu_item:contains("Foo")');
        assert.containsOnce(graph, '.o_menu_item:contains("Count")');
    });

    QUnit.test("graph view with invisible attribute on field", async function (assert) {
        assert.expect(2);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="revenue" invisible="1"/>
                </graph>
            `,
        });
        await toggleMenu(graph, "Measures");
        assert.containsN(
            graph,
            ".o_menu_item",
            2,
            "there should be only two menu item in the measures dropdown (count and foo)"
        );
        assert.containsNone(graph, '.o_menu_item:contains("Revenue")');
    });

    QUnit.test("graph view sort by measure", async function (assert) {
        assert.expect(20);

        // change first record from foo as there are 4 records count for each product
        serverData.models.product.records.push({ id: 38, display_name: "zphone" });
        serverData.models.foo.records[7].product_id = 38;

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph order="DESC">
                    <field name="product_id"/>
                </graph>
            `,
        });

        assert.containsOnce(graph, "button.fa-sort-amount-asc");
        assert.containsOnce(graph, "button.fa-sort-amount-desc");

        checkLegend(assert, graph, "Count", "measure should be by count");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            'sorting should be applie on descending order by default when sorting="desc"'
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });

        await click(graph.el, "button.fa-sort-amount-asc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order should be applied"
        );
        checkDatasets(assert, graph, "data", { data: [1, 3, 4] });

        await click(graph.el, "button.fa-sort-amount-desc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should be active"
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });

        // again click on descending button to deactivate order button
        await click(graph.el, "button.fa-sort-amount-desc");
        assert.doesNotHaveClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should not be active"
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });

        // set line mode
        await selectMode(graph, "line");
        assert.containsOnce(graph, "button.fa-sort-amount-asc");
        assert.containsOnce(graph, "button.fa-sort-amount-desc");

        checkLegend(assert, graph, "Count", "measure should be by count");
        assert.doesNotHaveClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order should be applied"
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });

        await click(graph.el, "button.fa-sort-amount-asc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order button should be active"
        );
        checkDatasets(assert, graph, "data", { data: [1, 3, 4] });

        await click(graph.el, "button.fa-sort-amount-desc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should be active"
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });
    });

    QUnit.test("graph view sort by measure for grouped data", async function (assert) {
        assert.expect(8);

        // change first record from foo as there are 4 records count for each product
        serverData.models.product.records.push({ id: 38, display_name: "zphone" });
        serverData.models.foo.records[7].product_id = 38;

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id"/>
                    <field name="bar"/>
                </graph>
            `,
        });

        checkLegend(assert, graph, ["true", "false"], "measure should be by count");
        checkDatasets(assert, graph, "data", [{ data: [3, 0, 0] }, { data: [1, 3, 1] }]);

        await click(graph.el, "button.fa-sort-amount-asc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order should be applied by default"
        );
        checkDatasets(assert, graph, "data", [{ data: [1, 3, 1] }, { data: [0, 0, 3] }]);

        await click(graph.el, "button.fa-sort-amount-desc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "ascending order button should be active"
        );
        checkDatasets(assert, graph, "data", [{ data: [3, 0, 0] }, { data: [1, 3, 1] }]);

        // again click on descending button to deactivate order button
        await click(graph.el, "button.fa-sort-amount-desc");
        assert.doesNotHaveClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should not be active"
        );
        checkDatasets(assert, graph, "data", [{ data: [3, 0, 0] }, { data: [1, 3, 1] }]);
    });

    QUnit.test("graph view sort by measure for multiple grouped data", async function (assert) {
        assert.expect(8);

        // change first record from foo as there are 4 records count for each product
        serverData.models.product.records.push({ id: 38, display_name: "zphone" });
        serverData.models.foo.records[7].product_id = 38;
        serverData.models.foo.records.splice(
            0,
            4,
            { id: 9, foo: 48, bar: false, product_id: 41, date: "2016-04-01" },
            { id: 10, foo: 49, bar: false, product_id: 41, date: "2016-04-01" },
            { id: 11, foo: 50, bar: true, product_id: 37, date: "2016-01-03" },
            { id: 12, foo: 50, bar: true, product_id: 41, date: "2016-01-03" }
        );

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="date"/>
                    <field name="product_id"/>
                </graph>
            `,
        });

        checkLegend(assert, graph, ["xpad", "xphone", "zphone"], "measure should be by count");
        checkDatasets(assert, graph, "data", [
            { data: [2, 1, 1, 2] },
            { data: [0, 1, 0, 0] },
            { data: [1, 0, 0, 0] },
        ]);

        await click(graph.el, "button.fa-sort-amount-asc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order should be applied by default"
        );
        checkDatasets(assert, graph, "data", [
            { data: [1, 1, 2, 2] },
            { data: [0, 1, 0, 0] },
            { data: [0, 0, 0, 1] },
        ]);

        await click(graph.el, "button.fa-sort-amount-desc");
        assert.hasClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should be active"
        );
        checkDatasets(assert, graph, "data", [
            { data: [2, 1, 2, 1] },
            { data: [1, 0, 0, 0] },
            { data: [0, 1, 0, 0] },
        ]);

        // again click on descending button to deactivate order button
        await click(graph.el, "button.fa-sort-amount-desc");
        assert.doesNotHaveClass(
            graph.el.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should not be active"
        );
        checkDatasets(assert, graph, "data", [
            { data: [2, 1, 1, 2] },
            { data: [0, 1, 0, 0] },
            { data: [1, 0, 0, 0] },
        ]);
    });

    QUnit.test("empty graph view with sample data", async function (assert) {
        assert.expect(8);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph sample="1">
                    <field name="product_id"/>
                    <field name="date"/>
                </graph>
            `,
            context: { search_default_false_domain: 1 },
            searchViewArch: `
                <search>
                    <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                </search>
            `,
            noContentHelp: '<p class="abc">click to add a foo</p>',
        });

        assert.hasClass(graph.el, "o_view_sample_data");
        assert.containsOnce(graph, ".o_view_nocontent");
        assert.containsOnce(graph, ".o_graph_canvas_container canvas");
        assert.hasClass(graph.el.querySelector(".o_graph_renderer"), "o_sample_data_disabled");

        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "False Domain");
        assert.doesNotHaveClass(graph.el, "o_view_sample_data");
        assert.containsNone(graph, ".o_view_nocontent");
        assert.containsOnce(graph, ".o_graph_canvas_container canvas");
        assert.doesNotHaveClass(
            graph.el.querySelector(".o_graph_renderer"),
            "o_sample_data_disabled"
        );
    });

    QUnit.test("non empty graph view with sample data", async function (assert) {
        assert.expect(8);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph sample="1">
                    <field name="product_id"/>
                    <field name="date"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]"/>
                </search>
            `,
            noContentHelp: '<p class="abc">click to add a foo</p>',
        });
        assert.doesNotHaveClass(graph.el, "o_view_sample_data");
        assert.containsNone(graph, ".o_view_nocontent");
        assert.containsOnce(graph, ".o_graph_canvas_container canvas");
        assert.doesNotHaveClass(
            graph.el.querySelector(".o_graph_canvas_container"),
            "o_sample_data_disabled"
        );
        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "False Domain");
        assert.doesNotHaveClass(graph.el, "o_view_sample_data");
        assert.containsOnce(graph, ".o_graph_canvas_container canvas");
        assert.doesNotHaveClass(
            graph.el.querySelector(".o_graph_canvas_container"),
            "o_sample_data_disabled"
        );
        assert.containsNone(graph, ".o_view_nocontent");
    });

    QUnit.test("reload chart with switchView button keep internal state", async function (assert) {
        assert.expect(3);
        serverData.views["foo,false,list"] = `<list/>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Foo Action 1",
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [
                [false, "graph"],
                [false, "list"],
            ],
        });
        assert.hasClass(getModeButton(webClient, "bar"), "active");
        await selectMode(webClient, "line");
        assert.hasClass(getModeButton(webClient, "line"), "active");
        await switchView(webClient, "graph");
        assert.hasClass(getModeButton(webClient, "line"), "active");
    });

    QUnit.test(
        "fallback on initial groupby when the groupby from control panel has 0 length",
        async function (assert) {
            assert.expect(2);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line">
                        <field name="product_id"/>
                    </graph>
                `,
                searchViewArch: `
                    <search>
                        <filter name="group_by_foo" string="Foo" domain="[]" context="{ 'group_by': 'foo'}"/>
                    </search>
                `,
                context: {
                    search_default_group_by_foo: 1,
                },
            });
            checkLabels(assert, graph, ["3", "53", "2", "24", "4", "63", "42", "48"]);
            await toggleGroupByMenu(graph);
            await toggleMenuItem(graph, "Foo");
            checkLabels(assert, graph, ["xphone", "xpad"]);
        }
    );

    QUnit.test(
        "change mode, stacked, or order via the graph buttons does not reload datapoints, change measure does",
        async function (assert) {
            assert.expect(13);
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line">
                        <field name="product_id"/>
                    </graph>
                `,
                mockRPC: function (_, args) {
                    if (args.method === "web_read_group") {
                        assert.step(JSON.stringify(args.kwargs.fields));
                    }
                },
            });

            checkModeIs(assert, graph, "line");

            await selectMode(graph, "bar");

            checkModeIs(assert, graph, "bar");
            assert.hasClass(graph.el.querySelector(`[data-tooltip="Stacked"]`), "active");

            await click(graph.el.querySelector(`[data-tooltip="Stacked"]`));

            assert.doesNotHaveClass(graph.el.querySelector(`[data-tooltip="Stacked"]`), "active");
            assert.doesNotHaveClass(graph.el.querySelector(`[data-tooltip="Ascending"]`), "active");

            await click(graph.el.querySelector(`[data-tooltip="Ascending"]`));

            assert.hasClass(graph.el.querySelector(`[data-tooltip="Ascending"]`), "active");

            await toggleMenu(graph, "Measures");
            await toggleMenuItem(graph, "Foo");

            assert.verifySteps([
                `["__count"]`, // first load
                `["__count","foo:sum"]`, // reload due to change in measure
            ]);
        }
    );

    QUnit.test(
        "concurrent reloads: add a filter, and directly toggle a measure",
        async function (assert) {
            let def;
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line">
                        <field name="product_id"/>
                    </graph>`,
                searchViewArch: `
                    <search>
                        <filter name="my_filter" string="My Filter" domain="[('id', '&lt;', 6)]"/>
                    </search>`,
                mockRPC: function (route, args) {
                    if (args.method === "web_read_group") {
                        return Promise.resolve(def);
                    }
                },
            });

            checkDatasets(assert, graph, ["data", "label"], {
                data: [4, 4],
                label: "Count",
            });

            // Set a domain (this reload is delayed)
            def = makeDeferred();
            await toggleFilterMenu(graph);
            await toggleMenuItem(graph, "My Filter");

            checkDatasets(assert, graph, ["data", "label"], {
                data: [4, 4],
                label: "Count",
            });

            // Toggle a measure
            await toggleMenu(graph, "Measures");
            await toggleMenuItem(graph, "Foo");

            checkDatasets(assert, graph, ["data", "label"], {
                data: [4, 4],
                label: "Count",
            });

            def.resolve();
            await nextTick();

            checkDatasets(assert, graph, ["data", "label"], {
                data: [82, 4],
                label: "Foo",
            });
        }
    );

    QUnit.test("change graph mode while loading a filter", async function (assert) {
        let def;
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line">
                    <field name="product_id"/>
                </graph>`,
            searchViewArch: `
                <search>
                    <filter name="my_filter" string="My Filter" domain="[('id', '&lt;', 2)]"/>
                </search>`,
            mockRPC: function (route, args) {
                if (args.method === "web_read_group") {
                    return Promise.resolve(def);
                }
            },
        });

        checkDatasets(assert, graph, ["data", "label"], {
            data: [4, 4],
            label: "Count",
        });
        checkModeIs(assert, graph, "line");

        // Set a domain (this reload is delayed)
        def = makeDeferred();
        await toggleFilterMenu(graph);
        await toggleMenuItem(graph, "My Filter");

        checkDatasets(assert, graph, ["data", "label"], {
            data: [4, 4],
            label: "Count",
        });
        checkModeIs(assert, graph, "line");

        // Change graph mode
        await selectMode(graph, "bar");

        checkDatasets(assert, graph, ["data", "label"], {
            data: [4, 4],
            label: "Count",
        });
        checkModeIs(assert, graph, "line");

        def.resolve();
        await nextTick();

        checkDatasets(assert, graph, ["data", "label"], {
            data: [1],
            label: "Count",
        });
        checkModeIs(assert, graph, "bar");
    });

    QUnit.test("only process most recent data for concurrent groupby", async function (assert) {
        assert.expect(6);

        let def;
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }"/>
                    <filter name="group_by_date" string="Date" context="{ 'group_by': 'date' }"/>
                </search>
            `,
            mockRPC() {
                return Promise.resolve(def);
            },
        });

        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkDatasets(assert, graph, "data", { data: [82, 157] });

        def = makeDeferred();
        await toggleGroupByMenu(graph);
        await toggleMenuItem(graph, "Color");
        await toggleMenuItem(graph, "Color");
        await toggleMenuItem(graph, "Date");
        await toggleMenuItemOption(graph, "Date", "Month");

        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkDatasets(assert, graph, "data", { data: [82, 157] });

        def.resolve();
        await nextTick();

        checkLabels(assert, graph, [
            "January 2016",
            "March 2016",
            "May 2016",
            "Undefined",
            "April 2016",
        ]);
        checkDatasets(assert, graph, "data", { data: [56, 26, 4, 105, 48] });
    });

    QUnit.test("fill_temporal is true by default", async function (assert) {
        assert.expect(1);

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            mockRPC: function (route, args) {
                if (args.method === "web_read_group") {
                    assert.strictEqual(
                        args.kwargs.context.fill_temporal,
                        true,
                        "The observal state of fill_temporal should be true"
                    );
                }
            },
        });
    });

    QUnit.test("fill_temporal can be changed throught the context", async function (assert) {
        assert.expect(1);

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            context: { fill_temporal: false },
            mockRPC: function (route, args) {
                if (args.method === "web_read_group") {
                    assert.strictEqual(
                        args.kwargs.context.fill_temporal,
                        false,
                        "The observal state of fill_temporal should be false"
                    );
                }
            },
        });
    });
});

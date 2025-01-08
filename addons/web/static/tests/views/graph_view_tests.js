/** @odoo-module **/

import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchDate,
    triggerEvent,
    findChildren,
} from "@web/../tests/helpers/utils";
import {
    editFavoriteName,
    saveFavorite,
    switchView,
    toggleComparisonMenu,
    toggleFavoriteMenu,
    toggleFilterMenu,
    toggleGroupByMenu,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    validateSearch,
} from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { getBorderWhite, DEFAULT_BG, getColors, hexToRGBA } from "@web/views/graph/colors";
import { GraphArchParser } from "@web/views/graph/graph_arch_parser";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { onRendered } from "@odoo/owl";
import { patchWithCleanup } from "../helpers/utils";
import { fakeCookieService } from "@web/../tests/helpers/mock_services";
import { Domain } from "@web/core/domain";
import { GraphModel } from "@web/views/graph/graph_model";

const serviceRegistry = registry.category("services");

function getGraphModelMetaData(graph) {
    return graph.model.metaData;
}

export function getGraphRenderer(graph) {
    const layoutNode = findChildren(graph);
    return Object.values(layoutNode.children)
        .map((c) => c.component)
        .find((c) => c.chart);
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
    assert.containsOnce(target, "div.o_graph_custom_tooltip");
    const tooltipTitle = target.querySelector("table thead tr th.o_measure");
    assert.strictEqual(tooltipTitle.innerText, title || "Count", `Tooltip title`);
    assert.deepEqual(
        [...target.querySelectorAll("table tbody tr td span.o_label")].map((td) => td.innerText),
        lineLabels,
        `Tooltip line labels`
    );
    assert.deepEqual(
        [...target.querySelectorAll("table tbody tr td.o_value")].map((td) => td.innerText),
        lineValues,
        `Tooltip line values`
    );
}

function getModeButton(el, mode) {
    return el.querySelector(`.o_graph_button[data-mode="${mode}"`);
}

async function selectMode(el, mode) {
    await click(getModeButton(el, mode));
}

function checkModeIs(assert, graph, mode) {
    assert.strictEqual(getGraphModelMetaData(graph).mode, mode);
    assert.strictEqual(getChart(graph).config.type, mode);
    assert.hasClass(getModeButton(target, mode), "active");
}

function getScaleY(graph) {
    return getChart(graph).config.options.scales.yAxes;
}

function getXAxeLabel(graph) {
    return getChart(graph).config.options.scales.xAxes[0].scaleLabel.labelString;
}

function getYAxeLabel(graph) {
    return getChart(graph).config.options.scales.yAxes[0].scaleLabel.labelString;
}

export async function clickOnDataset(graph) {
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
let target;
QUnit.module("Views", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                foo: {
                    fields: {
                        id: { string: "Id", type: "integer" },
                        foo: {
                            string: "Foo",
                            type: "integer",
                            store: true,
                            group_operator: "sum",
                            sortable: true,
                        },
                        bar: { string: "bar", type: "boolean", store: true, sortable: true },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            store: true,
                            sortable: true,
                        },
                        color_id: {
                            string: "Color",
                            type: "many2one",
                            relation: "color",
                            store: true,
                            sortable: true,
                        },
                        date: { string: "Date", type: "date", store: true, sortable: true },
                        revenue: {
                            string: "Revenue",
                            type: "float",
                            store: true,
                            group_operator: "sum",
                            sortable: true,
                        },
                        color_ids: {
                            string: "Colors",
                            type: "many2many",
                            relation: "color",
                            store: true,
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
                            color_ids: [7],
                        },
                        {
                            id: 2,
                            foo: 53,
                            bar: true,
                            product_id: 37,
                            color_id: 7,
                            date: "2016-01-03",
                            revenue: 2,
                            color_ids: [14],
                        },
                        {
                            id: 3,
                            foo: 2,
                            bar: true,
                            product_id: 37,
                            date: "2016-03-04",
                            revenue: 3,
                            color_ids: [7, 14],
                        },
                        {
                            id: 4,
                            foo: 24,
                            bar: false,
                            product_id: 37,
                            date: "2016-03-07",
                            revenue: 4,
                            color_ids: [7],
                        },
                        {
                            id: 5,
                            foo: 4,
                            bar: false,
                            product_id: 41,
                            date: "2016-05-01",
                            revenue: 5,
                            color_ids: [7, 14],
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
        setupViewRegistries();
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });

        target = getFixture();
        registry.category("services").add("cookie", fakeCookieService);
    });

    QUnit.module("GraphView");

    QUnit.test("simple bar chart rendering", async function (assert) {
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        const { measure, mode, order, stacked } = getGraphModelMetaData(graph);
        assert.hasClass(target.querySelector(".o_graph_view"), "o_view_controller");
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        assert.containsNone(target, ".o_nocontent_help");
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["false", "true"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "#1f77b4",
            borderColor: undefined,
            data: [5, 3],
            label: "Count",
        });
        checkLegend(assert, graph, "Count");
        checkTooltip(assert, graph, { lines: [{ label: "false", value: "5" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "true", value: "3" }] }, 1);
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["false", "true"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: "#1f77b4",
                    borderColor: undefined,
                    data: [1, 3],
                    label: "xphone",
                },
                {
                    backgroundColor: "#ff7f0e",
                    borderColor: undefined,
                    data: [4, 0],
                    label: "xpad",
                },
            ]
        );
        checkLegend(assert, graph, ["xphone", "xpad"]);
        checkTooltip(assert, graph, { lines: [{ label: "false / xphone", value: "1" }] }, 0, 0);
        checkTooltip(assert, graph, { lines: [{ label: "true / xphone", value: "3" }] }, 1, 0);
        checkTooltip(assert, graph, { lines: [{ label: "false / xpad", value: "4" }] }, 0, 1);
        checkTooltip(assert, graph, { lines: [{ label: "true / xpad", value: "0" }] }, 1, 1);
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

    QUnit.test("bar chart many2many groupBy", async function (assert) {
        assert.expect(16);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="revenue" type="measure"/>
                    <field name="color_ids"/>
                </graph>`,
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["Undefined", "black", "red"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "#1f77b4",
            borderColor: undefined,
            data: [8, 10, 13],
            label: "Revenue",
        });
        checkLegend(assert, graph, "Revenue");
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "Undefined", value: "8" }], title: "Revenue" },
            0
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "black", value: "10" }], title: "Revenue" },
            1
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "red", value: "13" }], title: "Revenue" },
            2
        );
    });

    QUnit.test("differentiate many2many values with same label", async function (assert) {
        assert.expect(19);
        serverData.models.color.records.push({ id: 21, display_name: "red" });
        serverData.models.foo.records.push({ id: 30, color_ids: [21], revenue: 14 });
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="revenue" type="measure"/>
                    <field name="color_ids"/>
                </graph>`,
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["Undefined", "black", "red", "red (2)"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "#1f77b4",
            borderColor: undefined,
            data: [8, 10, 14, 13],
            label: "Revenue",
        });

        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "Undefined", value: "8" }], title: "Revenue" },
            0
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "black", value: "10" }], title: "Revenue" },
            1
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "red", value: "14" }], title: "Revenue" },
            2
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "red (2)", value: "13" }], title: "Revenue" },
            3
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
                { date: "2021-01-04", bar: false, revenue: 12 },
                { date: "2021-01-12", bar: true, revenue: 5 },
                { date: "2021-02-04", bar: false, revenue: 14 },
                { date: "2021-02-17", bar: true, revenue: false },
                { date: false, bar: false, revenue: 0 },
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
            checkLabels(assert, graph, ["false", "true"]);
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
                    lines: [{ label: "false / February 2021 / W05 2021", value: "14" }],
                },
                0,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "false / January 2021 / W01 2021", value: "12" }],
                },
                0,
                2
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "true / January 2021 / W02 2021", value: "5" }],
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["false", "true"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "rgba(31,119,180,0.4)",
            borderColor: "#1f77b4",
            data: [5, 3],
            label: "Count",
        });
        checkLegend(assert, graph, "Count");
        checkTooltip(assert, graph, { lines: [{ label: "false", value: "5" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "true", value: "3" }] }, 1);
    });

    QUnit.test("line chart rendering (two groupBy)", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line" stacked="0">
                    <field name="bar"/>
                    <field name="product_id"/>
                </graph>
            `,
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["false", "true"]);
        checkDatasets(
            assert,
            graph,
            ["backgroundColor", "borderColor", "data", "label"],
            [
                {
                    backgroundColor: undefined,
                    borderColor: "#1f77b4",
                    data: [1, 3],
                    label: "xphone",
                },
                {
                    backgroundColor: undefined,
                    borderColor: "#ff7f0e",
                    data: [4, 0],
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
                    { label: "false / xpad", value: "4" },
                    { label: "false / xphone", value: "1" },
                ],
            },
            0
        );
        checkTooltip(
            assert,
            graph,
            {
                lines: [
                    { label: "true / xphone", value: "3" },
                    { label: "true / xpad", value: "0" },
                ],
            },
            1
        );
    });

    QUnit.test("line chart many2many groupBy", async function (assert) {
        assert.expect(12);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line">
                    <field name="revenue" type="measure"/>
                    <field name="color_ids"/>
                </graph>
            `,
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["black", "red"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: "rgba(31,119,180,0.4)",
            borderColor: "#1f77b4",
            data: [10, 13],
            label: "Revenue",
        });
        checkLegend(assert, graph, "Revenue");
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "black", value: "10" }], title: "Revenue" },
            0
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "red", value: "13" }], title: "Revenue" },
            1
        );
    });

    QUnit.test("Stacked button visible in the line chart", async function (assert) {
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
        await selectMode(target, "line");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(graph.model.metaData.stacked, true, "graph should be stacked.");
        assert.strictEqual(
            getScaleY(graph).every((y) => y.stacked),
            true,
            "The y axes should have stacked property set to true"
        );
        assert.containsOnce(target, `button.o_graph_button[data-tooltip="Stacked"]`);
        const stackButton = target.querySelector(`button.o_graph_button[data-tooltip="Stacked"]`);
        await click(stackButton);
        assert.strictEqual(
            graph.model.metaData.stacked,
            false,
            "graph should be a classic line chart."
        );
        assert.strictEqual(
            getScaleY(graph).every((y) => y.stacked == undefined),
            true,
            "The y axes should have stacked property set to undefined"
        );
    });

    QUnit.test("Stacked line prop click false", async function (assert) {
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

        const stackButton = target.querySelector(`button.o_graph_button[data-tooltip="Stacked"]`);
        await click(stackButton);
        assert.strictEqual(
            graph.model.metaData.stacked,
            false,
            "graph should be a classic line chart."
        );
        assert.strictEqual(
            getScaleY(graph).every((y) => y.stacked),
            false,
            "the y axes should have a stacked property set to false since the stacked property in line chart is false."
        );
        assert.strictEqual(
            getGraphRenderer(graph).getElementOptions().line.fill,
            false,
            "The fill property should be false since the stacked property is false."
        );

        const expectedDatasets = [
            {
                backgroundColor: undefined,
                borderColor: "#1f77b4",
                originIndex: 0,
                pointBackgroundColor: "#1f77b4",
            },
            {
                backgroundColor: undefined,
                borderColor: "#ff7f0e",
                originIndex: 0,
                pointBackgroundColor: "#ff7f0e",
            },
        ];
        const keysToEvaluate = [
            "backgroundColor",
            "borderColor",
            "originIndex",
            "pointBackgroundColor",
        ];
        checkDatasets(assert, graph, keysToEvaluate, expectedDatasets);
    });

    QUnit.test("Stacked prop and default line chart", async function (assert) {
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

        assert.strictEqual(graph.model.metaData.mode, "line", "should be in line chart mode.");
        assert.strictEqual(graph.model.metaData.stacked, true, "should be stacked by default.");

        assert.strictEqual(
            getScaleY(graph).every((y) => y.stacked),
            true,
            "the stacked property in y axes should be true when the stacked is enabled in line chart"
        );
        assert.strictEqual(
            getGraphRenderer(graph).getElementOptions().line.fill,
            true,
            "The fill property should be true to add backgroundColor in line chart."
        );

        const expectedDatasets = [];
        const keysToEvaluate = [
            "backgroundColor",
            "borderColor",
            "originIndex",
            "pointBackgroundColor",
        ];
        const datasets = getChart(graph).data.datasets;
        const colors = getColors();
        for (let i = 0; i < datasets.length; i++) {
            const expectedColor = colors[i];
            expectedDatasets.push({
                backgroundColor: hexToRGBA(expectedColor, 0.4),
                borderColor: expectedColor,
                originIndex: 0,
                pointBackgroundColor: expectedColor,
            });
        }
        checkDatasets(assert, graph, keysToEvaluate, expectedDatasets);
    });

    QUnit.test("Cumulative prop and default line chart", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line" stacked="0">
                    <field name="bar"/>
                    <field name="product_id"/>
                </graph>
            `,
        });

        assert.strictEqual(graph.model.metaData.mode, "line", "should be in line chart mode.");
        assert.strictEqual(
            graph.model.metaData.cumulated,
            false,
            "should not be cumulative by default."
        );

        await click(target, '[data-tooltip="Cumulative"]');
        assert.strictEqual(graph.model.metaData.cumulated, true, "should be in cumulative");
        const expectedDatasets = [
            {
                data: [1, 4],
            },
            {
                data: [4, 4],
            },
        ];
        checkDatasets(assert, graph, ["data"], expectedDatasets);
    });

    QUnit.test("Default cumulative prop", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="line" stacked="0" cumulated="1">
                    <field name="bar"/>
                    <field name="product_id"/>
                </graph>
            `,
        });

        assert.strictEqual(graph.model.metaData.mode, "line", "should be in line chart mode.");
        assert.strictEqual(graph.model.metaData.cumulated, true, "should be in cumulative");
    });

    QUnit.test("line chart rendering (no groupBy, several domains)", async function (assert) {
        assert.expect(7);
        const graph = await makeView({
            serverData,
            resModel: "foo",
            type: "graph",
            arch: `
                <graph type="line" stacked="0">
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
                <graph type="line" stacked="0">
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
        "line chart rendering (one groupBy, several domains with date identification) without stacked attribute",
        async function (assert) {
            serverData.models.foo.records = [
                { date: "2021-01-04", revenue: 12 },
                { date: "2021-01-12", revenue: 5 },
                { date: "2021-01-19", revenue: 15 },
                { date: "2021-01-26", revenue: 2 },
                { date: "2021-02-04", revenue: 14 },
                { date: "2021-02-17", revenue: false },
                { date: false, revenue: 0 },
            ];
            await makeView({
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
            assert.doesNotHaveClass(
                target.querySelector(".o_graph_button[data-tooltip=Stacked]"),
                "active",
                "The stacked mode should be disabled"
            );
        }
    );

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
                    <graph type="line" stacked="0">
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
                { date: "2021-01-04", bar: false, revenue: 12 },
                { date: "2021-01-12", bar: true, revenue: 5 },
                { date: "2021-02-04", bar: false, revenue: 14 },
                { date: "2021-02-17", bar: true, revenue: false },
                { date: false, bar: false, revenue: 0 },
            ];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph type="line" stacked="0">
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
            checkLabels(assert, graph, ["false", "true"]);
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
                        { label: "false / February 2021 / W05 2021", value: "14" },
                        { label: "false / January 2021 / W01 2021", value: "12" },
                        { label: "false / February 2021 / W07 2021", value: "0" },
                        { label: "false / January 2021 / W02 2021", value: "0" },
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
                        { label: "true / January 2021 / W02 2021", value: "5" },
                        { label: "true / February 2021 / W05 2021", value: "0" },
                        { label: "true / February 2021 / W07 2021", value: "0" },
                        { label: "true / January 2021 / W01 2021", value: "0" },
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
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="line" stacked="0"/>`,
        });
        assert.containsOnce(target, "canvas", "should have a canvas");
    });

    QUnit.test("pie chart rendering (no groupBy)", async function (assert) {
        assert.expect(9);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph type="pie"/>`,
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        const { mode } = getGraphModelMetaData(graph);
        assert.strictEqual(mode, "pie");
        checkLabels(assert, graph, ["Total"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label", "stack"], {
            backgroundColor: ["#1f77b4"],
            borderColor: getBorderWhite(),
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["false", "true"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data"], {
            backgroundColor: ["#1f77b4", "#ff7f0e"],
            borderColor: getBorderWhite(),
            data: [5, 3],
        });
        checkLegend(assert, graph, ["false", "true"]);
        checkTooltip(assert, graph, { lines: [{ label: "false", value: "5 (62.50%)" }] }, 0);
        checkTooltip(assert, graph, { lines: [{ label: "true", value: "3 (37.50%)" }] }, 1);
    });

    QUnit.test("pie chart many2many groupby", async function (assert) {
        assert.expect(16);
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph type="pie">
                    <field name="revenue" type="measure"/>
                    <field name="color_ids"/>
                </graph>
            `,
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["Undefined", "black", "red"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data"], {
            backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
            borderColor: getBorderWhite(),
            data: [8, 10, 13],
        });
        checkLegend(assert, graph, ["Undefined", "black", "red"]);
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "Undefined", value: "8 (25.81%)" }], title: "Revenue" },
            0
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "black", value: "10 (32.26%)" }], title: "Revenue" },
            1
        );
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "red", value: "13 (41.94%)" }], title: "Revenue" },
            2
        );
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
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        checkLabels(assert, graph, ["false / xphone", "false / xpad", "true / xphone"]);
        checkDatasets(assert, graph, ["backgroundColor", "borderColor", "data", "label"], {
            backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
            borderColor: getBorderWhite(),
            data: [1, 4, 3],
            label: "",
        });
        checkLegend(assert, graph, ["false / xphone", "false / xpad", "true / xphone"]);
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "false / xphone", value: "1 (12.50%)" }] },
            0
        );
        checkTooltip(assert, graph, { lines: [{ label: "false / xpad", value: "4 (50.00%)" }] }, 1);
        checkTooltip(
            assert,
            graph,
            { lines: [{ label: "true / xphone", value: "3 (37.50%)" }] },
            2
        );
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
                    borderColor: getBorderWhite(),
                    data: [6],
                    label: "True group",
                },
                {
                    backgroundColor: ["#1f77b4"],
                    borderColor: getBorderWhite(),
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
                    borderColor: getBorderWhite(),
                    data: [14, 0, 0],
                    label: "True group",
                },
                {
                    backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                    borderColor: getBorderWhite(),
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
                        borderColor: getBorderWhite(),
                        data: [1, 1, 0, 0],
                        label: "February 2021",
                    },
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8", "#ffbb78"],
                        borderColor: getBorderWhite(),
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
                { date: "2021-01-04", bar: false, revenue: 12 },
                { date: "2021-01-12", bar: true, revenue: 5 },
                { date: "2021-02-04", bar: false, revenue: 14 },
                { date: "2021-02-17", bar: true, revenue: false },
                { date: false, bar: false, revenue: 0 },
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
            checkLabels(assert, graph, ["false / W05 2021", "false / W01 2021", "true / W02 2021"]);
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label"],
                [
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                        borderColor: getBorderWhite(),
                        data: [14, 0, 0],
                        label: "February 2021",
                    },
                    {
                        backgroundColor: ["#1f77b4", "#ff7f0e", "#aec7e8"],
                        borderColor: getBorderWhite(),
                        data: [0, 12, 5],
                        label: "January 2021",
                    },
                ]
            );
            checkLegend(assert, graph, ["false / W05 2021", "false / W01 2021", "true / W02 2021"]);
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "February 2021 / false / W05 2021", value: "14 (100.00%)" }],
                },
                0,
                0
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "January 2021 / false / W01 2021", value: "12 (70.59%)" }],
                },
                1,
                1
            );
            checkTooltip(
                assert,
                graph,
                {
                    title: "Revenue",
                    lines: [{ label: "January 2021 / true / W02 2021", value: "5 (29.41%)" }],
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
                    borderColor: getBorderWhite(),
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
                    borderColor: getBorderWhite(),
                    data: [1],
                    label: "True group",
                },
                {
                    backgroundColor: ["#1f77b4", DEFAULT_BG],
                    borderColor: getBorderWhite(),
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
            assert.containsNone(target, ".o_view_nocontent");
            assert.containsOnce(target, ".o_graph_canvas_container");
            checkDatasets(
                assert,
                graph,
                ["backgroundColor", "borderColor", "data", "label", "stack"],
                {
                    backgroundColor: ["#1f77b4"],
                    borderColor: getBorderWhite(),
                    data: [2],
                    label: "",
                    stack: undefined,
                }
            );
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
        await selectMode(target, "line");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(getXAxeLabel(graph), "bar");
        await toggleMenu(target, "Measures");
        await toggleMenuItem(target, "Revenue");
        assert.strictEqual(getYAxeLabel(graph), "Revenue");
        assert.ok(true, "Message");
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Color");
        checkModeIs(assert, graph, "line");
        assert.strictEqual(getXAxeLabel(graph), "Color");
        assert.strictEqual(getYAxeLabel(graph), "Revenue");
    });

    QUnit.test("switching mode", async function (assert) {
        assert.expect(12);
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        checkModeIs(assert, graph, "bar");
        await selectMode(target, "bar"); // click on the active mode does not change anything
        checkModeIs(assert, graph, "bar");
        await selectMode(target, "line");
        checkModeIs(assert, graph, "line");
        await selectMode(target, "pie");
        checkModeIs(assert, graph, "pie");
    });

    QUnit.test("switching measure", async function (assert) {
        assert.expect(6);
        const graph = await makeView({ serverData, type: "graph", resModel: "foo" });
        function checkMeasure(measure) {
            const yAxe = getChart(graph).config.options.scales.yAxes[0];
            assert.strictEqual(yAxe.scaleLabel.labelString, measure);
            const item = [...target.querySelectorAll(".o_menu_item")].find(
                (el) => el.innerText === measure
            );
            assert.hasClass(item, "selected");
        }
        await toggleMenu(target, "Measures");
        checkMeasure("Count");
        checkLegend(assert, graph, "Count");
        await toggleMenuItem(target, "Foo");
        checkMeasure("Foo");
        checkLegend(assert, graph, "Foo");
    });

    QUnit.test("process default view description", async function (assert) {
        assert.expect(1);
        const propsFromArch = new GraphArchParser().parse();
        assert.deepEqual(propsFromArch, { fields: {}, fieldAttrs: {}, groupBy: [], measures: [] });
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
            measures: [],
            mode: "line",
            order: "ASC",
        });
        const arch2 = `<graph disable_linking="0" string="Title" stacked="False"/>`;
        propsFromArch = new GraphArchParser().parse(arch2, fields);

        assert.deepEqual(propsFromArch, {
            disableLinking: false,
            fields,
            fieldAttrs: {},
            groupBy: [],
            measures: [],
            stacked: false,
            title: "Title",
        });
    });

    QUnit.test("process arch with field tags", async function (assert) {
        assert.expect(1);
        const fields = serverData.models.foo.fields;
        fields.fighters = { type: "text", string: "Fighters" };
        const arch = `
            <graph type="pie">
                <field name="revenue" type="measure"/>
                <field name="date" interval="day"/>
                <field name="foo" modifiers='{"invisible": false}'/>
                <field name="bar" modifiers='{"invisible": true}' string="My invisible field"/>
                <field name="id"/>
                <field name="fighters" string="FooFighters"/>
            </graph>
        `;
        const propsFromArch = new GraphArchParser().parse(arch, fields);
        assert.deepEqual(propsFromArch, {
            fields,
            fieldAttrs: {
                bar: { isInvisible: true, string: "My invisible field" },
                fighters: { string: "FooFighters" },
            },
            measure: "revenue",
            measures: ["revenue"],
            groupBy: ["date:day", "foo"],
            mode: "pie",
        });
    });

    QUnit.test("process arch with non stored field tags of type measure", async function (assert) {
        assert.expect(1);
        const fields = serverData.models.foo.fields;
        fields.revenue.store = false;
        const arch = `
            <graph>
                <field name="product_id"/>
                <field name="revenue" type="measure"/>
                <field name="foo" type="measure"/>
            </graph>
        `;
        const propsFromArch = new GraphArchParser().parse(arch, fields);
        assert.deepEqual(propsFromArch, {
            fields,
            fieldAttrs: {},
            measure: "foo",
            measures: ["revenue", "foo"],
            groupBy: ["product_id"],
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
        checkLegend(assert, graph, ["false / Undefined", "true / Undefined", "true / red"]);

        await selectMode(target, "line");

        checkLabels(assert, graph, ["xphone", "xpad"]);
        checkLegend(assert, graph, ["false / Undefined", "true / Undefined", "true / red"]);

        await selectMode(target, "pie");

        checkLabels(assert, graph, [
            "xphone / false / Undefined",
            "xphone / true / Undefined",
            "xphone / true / red",
            "xpad / false / Undefined",
        ]);
        checkLegend(assert, graph, [
            "xphone / false / Undefined",
            "xphone / true / Undefined",
            "xphone / true / red",
            "xpad / false / Undefined",
        ]);
    });

    QUnit.test("no content helper", async function (assert) {
        assert.expect(3);
        serverData.models.foo.records = [];
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            noContentHelp: '<p class="abc">This helper should not be displayed in graph views</p>',
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        assert.containsNone(target, "div.o_view_nocontent");
        assert.containsNone(target, ".abc");
    });

    QUnit.test("no content helper after update", async function (assert) {
        assert.expect(6);
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            noContentHelp: '<p class="abc">This helper should not be displayed in graph views</p>',
            config: {
                views: [[false, "search"]],
            },
        });
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        assert.containsNone(target, "div.o_view_nocontent");
        assert.containsNone(target, ".abc");
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "False Domain");
        assert.containsOnce(target, "div.o_graph_canvas_container canvas");
        assert.containsNone(target, "div.o_view_nocontent");
        assert.containsNone(target, ".abc");
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
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Color");
        checkLabels(assert, graph, ["Undefined", "red"]);
    });

    QUnit.test("save params succeeds", async function (assert) {
        assert.expect(4);
        const expectedContexts = [
            {
                graph_mode: "bar",
                graph_measure: "__count",
                graph_groupbys: ["product_id"],
                graph_order: null,
                graph_stacked: true,
                group_by: [],
            },
            {
                graph_mode: "bar",
                graph_measure: "foo",
                graph_groupbys: ["product_id"],
                graph_order: null,
                graph_stacked: true,
                group_by: [],
            },
            {
                graph_mode: "line",
                graph_measure: "foo",
                graph_cumulated: false,
                graph_groupbys: ["product_id"],
                graph_order: null,
                graph_stacked: true,
                group_by: [],
            },
            {
                graph_mode: "line",
                graph_measure: "foo",
                graph_cumulated: false,
                graph_groupbys: ["product_id", "color_id"],
                graph_order: null,
                graph_stacked: true,
                group_by: ["product_id", "color_id"],
            },
        ];

        let serverId = 1;
        await makeView({
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

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "First Favorite");
        await saveFavorite(target);

        await toggleMenu(target, "Measures");
        await toggleMenuItem(target, "Foo");

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Second Favorite");
        await saveFavorite(target);

        await selectMode(target, "line");

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Third Favorite");
        await saveFavorite(target);

        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Product");
        await toggleMenuItem(target, "Color");

        await toggleFavoriteMenu(target);
        await toggleSaveFavorite(target);
        await editFavoriteName(target, "Fourth Favorite");
        await saveFavorite(target);
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
                { id: 1, bar: false, revenue: 1.5 },
                { id: 2, bar: true, revenue: 2 },
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
            checkLabels(assert, graph, ["false", "true"]);
            checkTooltip(
                assert,
                graph,
                { title: "Revenue", lines: [{ label: "false", value: "1.50" }] },
                0
            );
            checkTooltip(
                assert,
                graph,
                { title: "Revenue", lines: [{ label: "true", value: "2.00" }] },
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
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Nirvana");
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
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "Context");
        checkLegend(assert, graph, "Foo");
        assert.strictEqual(getYAxeLabel(graph), "Foo");
        checkModeIs(assert, graph, "line");
    });

    QUnit.test("reload graph with correct fields", async function (assert) {
        assert.expect(2);
        await makeView({
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
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "False Domain");
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
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "False Domain");
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
        checkLabels(assert, graph, ["false", "true"]);
        checkLegend(assert, graph, "Product");
        checkDatasets(assert, graph, "data", { data: [2, 1] });
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
        checkLabels(assert, graph, ["xphone", "xphone (2)", "xpad"]);
    });

    QUnit.test("not use a many2one as a measure by default", async function (assert) {
        assert.expect(1);
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: "<graph/>",
        });
        await toggleMenu(target, "Measures");
        assert.deepEqual(
            [...target.querySelectorAll(".o_cp_bottom_left .o_menu_item")].map(
                (el) => el.innerText
            ),
            ["Foo", "Revenue", "Count"]
        );
    });

    QUnit.test(
        "graph view crash when moving from search view using Down key",
        async function (assert) {
            assert.expect(1);
            await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `<graph/>`,
            });
            await triggerEvent(target, ".o_searchview input", "keydown", { key: "ArrowDown" });
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
            await makeView({
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
            await toggleMenu(target, "Measures");
            assert.deepEqual(
                [...target.querySelectorAll(".o_cp_bottom_left .o_menu_item")].map(
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
        "non store fields defined on the arch are present in the measures",
        async function (assert) {
            serverData.models.foo.fields.revenue.store = false;
            await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `<graph>
                <field name="product_id"/>
                <field name="revenue" type="measure"/>
                <field name="foo" type="measure"/>
            </graph>`,
            });
            await toggleMenu(target, "Measures");
            assert.deepEqual(
                Array.from(target.querySelectorAll(".o_menu_item")).map((e) => e.innerText.trim()),
                ["Foo", "Revenue", "Count"]
            );
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
            await selectMode(target, "bar");
            assert.ok(someUndefined());
            await selectMode(target, "pie");
            assert.ok(someUndefined());
            // Undefined should not appear after switching back to line chart
            await selectMode(target, "line");
            assert.notOk(someUndefined());
        }
    );

    QUnit.test(
        "an invisible field can not be found in the 'Measures' menu",
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
            await toggleMenu(target, "Measures");
            assert.notOk(
                [...target.querySelectorAll(".o_menu_item")].find(
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
        const target = getFixture();
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Glou glou",
            res_model: "foo",
            type: "ir.actions.act_window",
            views: [[false, "graph"]],
        });
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item.active").innerText,
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
                                domain: [["bar", "=", false]],
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
            domains: [[["bar", "=", false]], [["bar", "=", true]]],
        });
        await clickOnDataset(graph);
    });

    QUnit.test(
        "Clicking on bar charts removes group_by and search_default_* context keys",
        async function (assert) {
            assert.expect(2);

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
                                    domain: [["bar", "=", false]],
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
                context: {
                    search_default_user: 1,
                    group_by: "bar",
                },
            });

            await clickOnDataset(graph);
        }
    );

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
                                    domain: [["bar", "=", false]],
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
                domains: [[["bar", "=", false]], [["bar", "=", true]]],
            });
            await clickOnDataset(graph);
        }
    );

    QUnit.test('graph view with attribute disable_linking="1"', async function (assert) {
        assert.expect(4);

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
            domains: [[["bar", "=", false]], [["bar", "=", true]]],
        });
        await clickOnDataset(graph);
    });

    QUnit.test("graph view without invisible attribute on field", async function (assert) {
        assert.expect(4);
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `<graph/>`,
        });
        await toggleMenu(target, "Measures");
        assert.containsN(
            target,
            ".o_menu_item",
            3,
            "there should be three menu item in the measures dropdown (count, revenue and foo)"
        );
        assert.containsOnce(target, '.o_menu_item:contains("Revenue")');
        assert.containsOnce(target, '.o_menu_item:contains("Foo")');
        assert.containsOnce(target, '.o_menu_item:contains("Count")');
    });

    QUnit.test("graph view with invisible attribute on field", async function (assert) {
        assert.expect(2);
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="revenue" invisible="1"/>
                </graph>
            `,
        });
        await toggleMenu(target, "Measures");
        assert.containsN(
            target,
            ".o_menu_item",
            2,
            "there should be only two menu item in the measures dropdown (count and foo)"
        );
        assert.containsNone(target, '.o_menu_item:contains("Revenue")');
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

        assert.containsOnce(target, "button.fa-sort-amount-asc");
        assert.containsOnce(target, "button.fa-sort-amount-desc");

        checkLegend(assert, graph, "Count", "measure should be by count");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            'sorting should be applie on descending order by default when sorting="desc"'
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });

        await click(target, "button.fa-sort-amount-asc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order should be applied"
        );
        checkDatasets(assert, graph, "data", { data: [1, 3, 4] });

        await click(target, "button.fa-sort-amount-desc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should be active"
        );
        checkDatasets(assert, graph, "data", { data: [4, 3, 1] });

        // again click on descending button to deactivate order button
        await click(target, "button.fa-sort-amount-desc");
        assert.doesNotHaveClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should not be active"
        );
        checkDatasets(assert, graph, "data", { data: [4, 1, 3] });

        // set line mode
        await selectMode(target, "line");
        assert.containsOnce(target, "button.fa-sort-amount-asc");
        assert.containsOnce(target, "button.fa-sort-amount-desc");

        checkLegend(assert, graph, "Count", "measure should be by count");
        assert.doesNotHaveClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order should be applied"
        );
        checkDatasets(assert, graph, "data", { data: [4, 1, 3] });

        await click(target, "button.fa-sort-amount-asc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order button should be active"
        );
        checkDatasets(assert, graph, "data", { data: [1, 3, 4] });

        await click(target, "button.fa-sort-amount-desc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-desc"),
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

        checkLegend(assert, graph, ["false", "true"], "measure should be by count");
        checkDatasets(assert, graph, "data", [{ data: [1, 1, 3] }, { data: [3, 0, 0] }]);

        await click(target, "button.fa-sort-amount-asc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order should be applied by default"
        );
        checkDatasets(assert, graph, "data", [{ data: [1, 3, 1] }, { data: [0, 0, 3] }]);

        await click(target, "button.fa-sort-amount-desc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "ascending order button should be active"
        );
        checkDatasets(assert, graph, "data", [{ data: [1, 3, 1] }, { data: [3, 0, 0] }]);

        // again click on descending button to deactivate order button
        await click(target, "button.fa-sort-amount-desc");
        assert.doesNotHaveClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should not be active"
        );
        checkDatasets(assert, graph, "data", [{ data: [1, 1, 3] }, { data: [3, 0, 0] }]);
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

        checkLegend(assert, graph, ["xphone", "xpad", "zphone"], "measure should be by count");
        checkDatasets(assert, graph, "data", [
            { data: [1, 0, 0, 0] },
            { data: [1, 2, 1, 2] },
            { data: [0, 1, 0, 0] },
        ]);

        await click(target, "button.fa-sort-amount-asc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-asc"),
            "active",
            "ascending order should be applied by default"
        );
        checkDatasets(assert, graph, "data", [
            { data: [1, 1, 2, 2] },
            { data: [0, 1, 0, 0] },
            { data: [0, 0, 0, 1] },
        ]);

        await click(target, "button.fa-sort-amount-desc");
        assert.hasClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should be active"
        );
        checkDatasets(assert, graph, "data", [
            { data: [1, 0, 0, 0] },
            { data: [2, 1, 2, 1] },
            { data: [0, 1, 0, 0] },
        ]);

        // again click on descending button to deactivate order button
        await click(target, "button.fa-sort-amount-desc");
        assert.doesNotHaveClass(
            target.querySelector("button.fa-sort-amount-desc"),
            "active",
            "descending order button should not be active"
        );
        checkDatasets(assert, graph, "data", [
            { data: [1, 0, 0, 0] },
            { data: [1, 2, 1, 2] },
            { data: [0, 1, 0, 0] },
        ]);
    });

    QUnit.test("empty graph view with sample data", async function (assert) {
        await makeView({
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

        assert.hasClass(target.querySelector(".o_graph_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent");
        assert.containsOnce(target, ".o_graph_canvas_container canvas");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "False Domain");

        assert.doesNotHaveClass(
            target.querySelector(".o_graph_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, ".o_graph_canvas_container canvas");
    });

    QUnit.test("non empty graph view with sample data", async function (assert) {
        await makeView({
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
        assert.doesNotHaveClass(target, "o_view_sample_data");
        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, ".o_graph_canvas_container canvas");

        await toggleFilterMenu(target);
        await toggleMenuItem(target, "False Domain");

        assert.doesNotHaveClass(target, "o_view_sample_data");
        assert.containsOnce(target, ".o_graph_canvas_container canvas");
        assert.containsOnce(target, ".o_view_nocontent");
    });

    QUnit.test("empty graph view without sample data after filter", async function (assert) {
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph>
                    <field name="date"/>
                </graph>
            `,
            domain: Domain.FALSE.toList(),
            noContentHelp: '<p class="abc">click to add a foo</p>',
        });
        assert.containsOnce(target, ".o_graph_canvas_container canvas");
        assert.containsOnce(target, ".o_view_nocontent");
    });

    QUnit.test("reload chart with switchView button keep internal state", async function (assert) {
        assert.expect(3);
        serverData.views["foo,false,list"] = `<list/>`;
        const target = getFixture();
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
        assert.hasClass(getModeButton(target, "bar"), "active");
        await selectMode(target, "line");
        assert.hasClass(getModeButton(target, "line"), "active");
        await switchView(target, "graph");
        assert.hasClass(getModeButton(target, "line"), "active");
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
            checkLabels(assert, graph, ["2", "3", "4", "24", "42", "48", "53", "63"]);
            await toggleGroupByMenu(target);
            await toggleMenuItem(target, "Foo");
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

            await selectMode(target, "bar");

            checkModeIs(assert, graph, "bar");
            assert.hasClass(target.querySelector(`[data-tooltip="Stacked"]`), "active");

            await click(target.querySelector(`[data-tooltip="Stacked"]`));

            assert.doesNotHaveClass(target.querySelector(`[data-tooltip="Stacked"]`), "active");
            assert.doesNotHaveClass(target.querySelector(`[data-tooltip="Ascending"]`), "active");

            await click(target.querySelector(`[data-tooltip="Ascending"]`));

            assert.hasClass(target.querySelector(`[data-tooltip="Ascending"]`), "active");

            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Foo");

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
            await toggleFilterMenu(target);
            await toggleMenuItem(target, "My Filter");

            checkDatasets(assert, graph, ["data", "label"], {
                data: [4, 4],
                label: "Count",
            });

            // Toggle a measure
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Foo");

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
        await toggleFilterMenu(target);
        await toggleMenuItem(target, "My Filter");

        checkDatasets(assert, graph, ["data", "label"], {
            data: [4, 4],
            label: "Count",
        });
        checkModeIs(assert, graph, "line");

        // Change graph mode
        await selectMode(target, "bar");

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
        await toggleGroupByMenu(target);
        await toggleMenuItem(target, "Color");
        await toggleMenuItem(target, "Color");
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "Month");

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

        await makeView({
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

        await makeView({
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

    QUnit.test("fake data in line chart", async function (assert) {
        assert.expect(1);

        patchDate(2020, 4, 19, 1, 0, 0);

        serverData.models.foo.records = [];

        const graph = await makeView({
            type: "graph",
            resModel: "foo",
            serverData,
            context: { search_default_date_filter: 1 },
            arch: `
                <graph type="line">
                    <field name="date"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="date_filter" domain="[]" date="date" default_period="third_quarter"/>
                </search>
            `,
        });

        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous period");

        checkLabels(assert, graph, ["", ""]);
    });

    QUnit.test("no filling color for period of comparison", async function (assert) {
        assert.expect(1);

        patchDate(2020, 4, 19, 1, 0, 0);

        serverData.models.foo.records.forEach((r) => {
            if (r.date) {
                r.date = r.date.replace(/\d\d\d\d/, "2019");
            }
        });

        const graph = await makeView({
            type: "graph",
            resModel: "foo",
            serverData,
            context: { search_default_date_filter: 1 },
            arch: `
                <graph type="line" stacked="0">
                    <field name="product_id"/>
                </graph>
            `,
            searchViewArch: `
                <search>
                    <filter name="date_filter" domain="[]" date="date" default_period="this_year"/>
                </search>
            `,
        });

        await toggleComparisonMenu(target);
        await toggleMenuItem(target, "Date: Previous period");

        checkDatasets(assert, graph, "backgroundColor", {
            backgroundColor: undefined,
        });
    });

    QUnit.test("group by a non stored, sortable field", async function (assert) {
        assert.expect(1);
        // When a field is non-stored but sortable it's inherited
        // from a stored field, so it can be sortable
        serverData.models.foo.fields.date.store = false;
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            groupBy: ["date:month"],
            arch: `<graph type="line"/>`,
            config: {
                views: [[false, "search"]],
            },
        });
        checkLabels(assert, graph, ["January 2016", "March 2016", "May 2016", "April 2016"]);
    });

    QUnit.test("graph_groupbys should be also used after first load", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            groupBy: ["date:quarter"],
            arch: `<graph/>`,
            irFilters: [
                {
                    user_id: [2, "Mitchell Admin"],
                    name: "Favorite",
                    id: 1,
                    context: `{
                        "group_by": [],
                        "graph_measure": "revenue",
                        "graph_mode": "bar",
                        "graph_groupbys": ["color_id"],
                    }`,
                    sort: "[]",
                    domain: "",
                    is_default: false,
                    model_id: "foo",
                    action_id: false,
                },
            ],
        });

        checkModeIs(assert, graph, "bar");
        checkLabels(assert, graph, ["Q1 2016", "Q2 2016", "Undefined"]);
        checkLegend(assert, graph, "Count");

        await toggleFavoriteMenu(target);
        await toggleMenuItem(target, "Favorite");

        checkModeIs(assert, graph, "bar");
        checkLabels(assert, graph, ["Undefined", "red"]);
        checkLegend(assert, graph, "Revenue");
    });

    QUnit.test("order='desc' on arch", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph order="desc">
                    <field name="date"/>
                </graph>
            `,
        });
        checkDatasets(assert, graph, ["data", "label"], {
            data: [2, 2, 2, 1, 1],
            label: "Count",
        });
    });

    QUnit.test("order='asc' on arch", async function (assert) {
        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
            arch: `
                <graph order="asc">
                    <field name="date"/>
                </graph>
            `,
        });
        checkDatasets(assert, graph, ["data", "label"], {
            data: [1, 1, 2, 2, 2],
            label: "Count",
        });
    });

    QUnit.test("renders banner_route", async (assert) => {
        await makeView({
            type: "graph",
            resModel: "foo",
            serverData,
            arch: `
                <graph banner_route="/mybody/isacage">
                    <field name="foo"/>
                </graph>`,
            async mockRPC(route) {
                if (route === "/mybody/isacage") {
                    assert.step(route);
                    return { html: `<div class="setmybodyfree">myBanner</div>` };
                }
            },
        });

        assert.verifySteps(["/mybody/isacage"]);
        assert.containsOnce(target, ".setmybodyfree");
    });

    QUnit.test(
        "no class 'o_view_sample_data' when real data are presented",
        async function (assert) {
            serverData.models.foo.records = [];
            const graph = await makeView({
                serverData,
                type: "graph",
                resModel: "foo",
                arch: `
                    <graph sample="1">
                        <field name="date"/>
                    </graph>
                `,
            });
            assert.containsOnce(target, ".o_graph_view .o_view_sample_data");
            assert.ok(getChart(graph).data.datasets.length);
            await selectMode(target, "line");
            assert.containsOnce(target, ".o_graph_view .o_view_sample_data");
            assert.ok(getChart(graph).data.datasets.length);
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Revenue");
            assert.containsNone(target, ".o_graph_view .o_view_sample_data");
            assert.notOk(getChart(graph).data.datasets.length);
        }
    );

    QUnit.test("single chart rendering on search", async function (assert) {
        patchWithCleanup(GraphRenderer.prototype, {
            setup() {
                this._super(...arguments);
                onRendered(() => {
                    assert.step("rendering");
                });
            },
        });
        await makeView({
            serverData,
            type: "graph",
            resModel: "foo",
        });
        assert.verifySteps(["rendering"]);
        await validateSearch(target);
        assert.verifySteps(["rendering"]);
    });

    QUnit.test("limit dataset amount", async function (assert) {
        serverData.models.project = {
            fields: {
                id: { type: "integer" },
                name: { type: "char" },
            },
            records: [],
        };
        serverData.models.stage = {
            fields: {
                id: { type: "integer" },
                name: { type: "char" },
            },
            records: [],
        };
        serverData.models.task = {
            fields: {
                id: { type: "integer" },
                name: { type: "char" },
                project_id: {
                    type: "many2one",
                    relation: "project",
                    sortable: true,
                    string: "Project",
                },
                stage_id: { type: "many2one", relation: "stage", sortable: true, string: "Stage" },
            },
            records: [],
        };
        for (let i = 1; i <= 600; i++) {
            serverData.models.project.records.push({
                id: i,
                name: `Project ${i}`,
            });
            serverData.models.stage.records.push({
                id: i,
                name: `Stage ${i}`,
            });
            serverData.models.task.records.push({
                id: i,
                project_id: i,
                stage_id: i,
                name: `Task ${i}`,
            });
        }

        const graph = await makeView({
            serverData,
            type: "graph",
            resModel: "task",
            arch: `
                <graph>
                    <field name="project_id"/>
                    <field name="stage_id"/>
                </graph>
            `,
        });

        assert.strictEqual(graph.model.data.exceeds, true);
        assert.strictEqual(graph.model.data.datasets.length, 80);
        assert.strictEqual(graph.model.data.labels.length, 80);
        assert.containsN(target, `.o_graph_alert`, 1);

        patchWithCleanup(GraphModel.prototype, {
            notify() {
                assert.step("rerender");
            },
        });
        await click(target, `.o_graph_load_all_btn`);
        assert.verifySteps(["rerender"]);
        assert.strictEqual(graph.model.data.exceeds, false);
        assert.strictEqual(graph.model.data.datasets.length, 600);
        assert.strictEqual(graph.model.data.labels.length, 600);
    });
});

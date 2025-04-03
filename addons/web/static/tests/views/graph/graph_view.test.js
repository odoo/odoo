import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockDate } from "@odoo/hoot-mock";
import { onRendered } from "@odoo/owl";
import {
    contains,
    defineModels,
    editFavoriteName,
    fields,
    getService,
    makeMockServer,
    mockService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    saveFavorite,
    switchView,
    toggleMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleSaveFavorite,
    toggleSearchBarMenu,
    validateSearch,
} from "@web/../tests/web_test_helpers";
import {
    checkDatasets,
    checkLabels,
    checkLegend,
    checkModeIs,
    checkTooltip,
    checkYTicks,
    clickOnDataset,
    clickOnLegend,
    clickSort,
    getChart,
    getGraphModel,
    getGraphModelMetaData,
    getGraphRenderer,
    getModeButton,
    getScaleY,
    getYAxisLabel,
    selectMode,
    setupChartJsForTests,
} from "./graph_test_helpers";

import { DEFAULT_BG, getBorderWhite, getColors, lightenColor } from "@web/core/colors/colors";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { SampleServer } from "@web/model/sample_server";
import { GraphArchParser } from "@web/views/graph/graph_arch_parser";
import { GraphModel } from "@web/views/graph/graph_model";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";
import { WebClient } from "@web/webclient/webclient";

class Color extends models.Model {
    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "black",
        },
        {
            id: 2,
            name: "red",
        },
    ];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [
        {
            id: 100,
            name: "xphone",
        },
        {
            id: 200,
            name: "xpad",
        },
    ];
}

class Foo extends models.Model {
    bar = fields.Boolean({ default: false });
    color_id = fields.Many2one({ relation: "color" });
    color_ids = fields.Many2many({ relation: "color" });
    date = fields.Date();
    foo = fields.Integer();
    product_id = fields.Many2one({ relation: "product" });
    revenue = fields.Float();

    _records = [
        {
            id: 1,
            foo: 3,
            bar: true,
            product_id: 100,
            date: "2016-01-01",
            revenue: 1,
            color_ids: [2],
        },
        {
            id: 2,
            foo: 53,
            bar: true,
            product_id: 100,
            color_id: 2,
            date: "2016-01-03",
            revenue: 2,
            color_ids: [1],
        },
        {
            id: 3,
            foo: 2,
            bar: true,
            product_id: 100,
            date: "2016-03-04",
            revenue: 3,
            color_ids: [1, 2],
        },
        {
            id: 4,
            foo: 24,
            product_id: 100,
            date: "2016-03-07",
            revenue: 4,
            color_ids: [2],
        },
        {
            id: 5,
            foo: 4,
            product_id: 200,
            date: "2016-05-01",
            revenue: 5,
            color_ids: [1, 2],
        },
        {
            id: 6,
            foo: 63,
            product_id: 200,
        },
        {
            id: 7,
            foo: 42,
            product_id: 200,
        },
        {
            id: 8,
            foo: 48,
            product_id: 200,
            date: "2016-04-01",
            revenue: 8,
        },
    ];
    _views = {
        search: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]" />
                <filter name="filter_with_context"
                    string="Filter With Context"
                    domain="[]"
                    context="{ 'graph_measure': 'foo', 'graph_mode': 'line', 'graph_groupbys': ['color_id'] }"
                />
                <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }" />
                <filter name="group_by_product" string="Product" context="{ 'group_by': 'product_id' }" />
            </search>
        `,
    };
}

defineModels([Foo, Color, Product]);

setupChartJsForTests();

test('graph view with "class" attribute', async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        arch: `<graph class="foobar-class"/>`,
    });
    expect(".o_graph_view").toHaveClass("foobar-class");
});

test("simple bar chart rendering", async () => {
    const view = await mountView({ type: "graph", resModel: "foo" });

    const { measure, mode, order, stacked } = getGraphModelMetaData(view);

    expect(".o_graph_view").toHaveClass("o_view_controller");
    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(measure).toBe("__count", {
        message: `the active measure should be "__count" by default`,
    });
    expect(mode).toBe("bar", { message: "should be in bar chart mode by default" });
    expect(order).toBe(null, { message: "should not be ordered by default" });
    expect(stacked).toBe(true, { message: "bar charts should be stacked by default" });

    checkLabels(view, ["Total"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label", "stack"], {
        backgroundColor: "#4EA7F2",
        borderColor: undefined,
        data: [8],
        label: "Count",
        stack: "",
    });
    checkLegend(view, "Count");
    checkTooltip(view, { lines: [{ label: "Total", value: "8" }] }, 0);
});

test("simple bar chart rendering with no data", async () => {
    Foo._records = [];

    const view = await mountView({ type: "graph", resModel: "foo" });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(".o_nocontent_help").toHaveCount(0);
    checkLabels(view, []);
    checkDatasets(view, [], []);
});

test("simple bar chart rendering (one groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="bar" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["false", "true"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label"], {
        backgroundColor: "#4EA7F2",
        borderColor: undefined,
        data: [5, 3],
        label: "Count",
    });
    checkLegend(view, "Count");
    checkTooltip(view, { lines: [{ label: "false", value: "5" }] }, 0);
    checkTooltip(view, { lines: [{ label: "true", value: "3" }] }, 1);
});

test("simple bar chart rendering (two groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["false", "true"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#4EA7F2",
                borderColor: undefined,
                data: [1, 3],
                label: "xphone",
            },
            {
                backgroundColor: "#EA6175",
                borderColor: undefined,
                data: [4, 0],
                label: "xpad",
            },
            {
                backgroundColor: "#343a40",
                borderColor: "rgba(0,0,0,.3)",
                data: [5, 3],
                label: "Sum",
            },
        ]
    );
    checkLegend(view, ["xphone", "xpad", "Sum"]);
    checkTooltip(view, { lines: [{ label: "false / xphone", value: "1" }] }, 0, 0);
    checkTooltip(view, { lines: [{ label: "true / xphone", value: "3" }] }, 1, 0);
    checkTooltip(view, { lines: [{ label: "false / xpad", value: "4" }] }, 0, 1);
    checkTooltip(view, { lines: [{ label: "true / xpad", value: "0" }] }, 1, 1);
});

test("bar chart rendering (no groupBy, several domains)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
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

    checkLabels(view, ["Total"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#4EA7F2",
                borderColor: undefined,
                data: [6],
                label: "True group",
            },
            {
                backgroundColor: "#EA6175",
                borderColor: undefined,
                data: [17],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["True group", "False group"]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "Total / True group", value: "6" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "Total / False group", value: "17" }],
        },
        0,
        1
    );
});

test("bar chart rendering (one groupBy, several domains)", async () => {
    Foo._records = [
        { bar: true, foo: 1, revenue: 14 },
        { bar: true, foo: 2, revenue: 0 },
        { bar: false, foo: 1, revenue: 12 },
        { bar: false, foo: 2, revenue: -4 },
        { bar: false, foo: 3, revenue: 2 },
        { bar: false, foo: 4, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
                <field name="foo" />
            </graph>
        `,
        comparison: {
            domains: [
                { arrayRepr: [["bar", "=", true]], description: "True group" },
                { arrayRepr: [["bar", "=", false]], description: "False group" },
            ],
        },
    });

    checkLabels(view, ["1", "2", "3", "4"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#4EA7F2",
                borderColor: undefined,
                data: [14, 0, 0, 0],
                label: "True group",
            },
            {
                backgroundColor: "#EA6175",
                borderColor: undefined,
                data: [12, -4, 2, 0],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["True group", "False group"]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "1 / True group", value: "14" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "1 / False group", value: "12" }],
        },
        0,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "2 / False group", value: "-4" }],
        },
        1,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "3 / False group", value: "2" }],
        },
        2,
        1
    );
});

test("bar chart many2many groupBy", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
                <field name="color_ids" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["black", "red", "None"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label"], {
        backgroundColor: "#4EA7F2",
        borderColor: undefined,
        data: [10, 13, 8],
        label: "Revenue",
    });
    checkLegend(view, "Revenue");
    checkTooltip(view, { lines: [{ label: "black", value: "10" }], title: "Revenue" }, 0);
    checkTooltip(view, { lines: [{ label: "red", value: "13" }], title: "Revenue" }, 1);
    checkTooltip(view, { lines: [{ label: "None", value: "8" }], title: "Revenue" }, 2);
});

test("differentiate many2many values with same label", async () => {
    Color._records.push({ id: 3, name: "red" });
    Foo._records.push({ color_ids: [3], revenue: 14 });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
                <field name="color_ids" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["black", "red", "red (2)", "None"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label"], {
        backgroundColor: "#4EA7F2",
        borderColor: undefined,
        data: [10, 13, 14, 8],
        label: "Revenue",
    });
    checkTooltip(view, { lines: [{ label: "black", value: "10" }], title: "Revenue" }, 0);
    checkTooltip(view, { lines: [{ label: "red", value: "13" }], title: "Revenue" }, 1);
    checkTooltip(view, { lines: [{ label: "red (2)", value: "14" }], title: "Revenue" }, 2);
    checkTooltip(view, { lines: [{ label: "None", value: "8" }], title: "Revenue" }, 3);
});

test("bar chart rendering (one groupBy, several domains with date identification)", async () => {
    Foo._records = [
        { date: "2021-01-04", revenue: 12 },
        { date: "2021-01-12", revenue: 5 },
        { date: "2021-01-19", revenue: 15 },
        { date: "2021-01-26", revenue: 2 },
        { date: "2021-02-04", revenue: 14 },
        { date: "2021-02-17", revenue: 0 },
        { date: false, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
                <field name="date" interval="week" />
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

    checkLabels(view, ["W05 2021", "W07 2021", "", ""]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#4EA7F2",
                borderColor: undefined,
                data: [14, 0],
                label: "February 2021",
            },
            {
                backgroundColor: "#EA6175",
                borderColor: undefined,
                data: [12, 5, 15, 2],
                label: "January 2021",
            },
        ]
    );
    checkLegend(view, ["February 2021", "January 2021"]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "W05 2021 / February 2021", value: "14" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "W01 2021 / January 2021", value: "12" }],
        },
        0,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "W02 2021 / January 2021", value: "5" }],
        },
        1,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "W03 2021 / January 2021", value: "15" }],
        },
        2,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "W04 2021 / January 2021", value: "2" }],
        },
        3,
        1
    );
});

test("bar chart rendering (two groupBy, several domains with no date identification)", async () => {
    Foo._records = [
        { date: "2021-01-04", bar: false, revenue: 12 },
        { date: "2021-01-12", bar: true, revenue: 5 },
        { date: "2021-02-04", bar: false, revenue: 14 },
        { date: "2021-02-17", bar: true, revenue: 0 },
        { date: false, bar: false, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
                <field name="bar" />
                <field name="date" interval="week" />
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

    checkLabels(view, ["false", "true"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#4EA7F2",
                borderColor: undefined,
                data: [14, 0],
                label: "February 2021 / W05 2021",
            },
            {
                backgroundColor: "#EA6175",
                borderColor: undefined,
                data: [0, 0],
                label: "February 2021 / W07 2021",
            },
            {
                backgroundColor: "#43C5B1",
                borderColor: undefined,
                data: [12, 0],
                label: "January 2021 / W01 2021",
            },
            {
                backgroundColor: "#F4A261",
                borderColor: undefined,
                data: [0, 5],
                label: "January 2021 / W02 2021",
            },
        ]
    );
    checkLegend(view, [
        "February 2021 / W05 2021",
        "February 2021 / W07 2021",
        "January 2021 / W01 2021",
        "January 2021 / W02 2021",
    ]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "false / February 2021 / W05 2021", value: "14" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "false / January 2021 / W01 2021", value: "12" }],
        },
        0,
        2
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "true / January 2021 / W02 2021", value: "5" }],
        },
        1,
        3
    );
});

test("line chart rendering (no groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `<graph type="line" />`,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(getGraphModelMetaData(view).mode).toBe("line");
    checkLabels(view, ["", "Total", ""]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label", "stack"], {
        backgroundColor: "#a7d3f9",
        borderColor: "#4EA7F2",
        data: [undefined, 8],
        label: "Count",
        stack: undefined,
    });
    checkLegend(view, "Count");
    checkTooltip(view, { lines: [{ label: "Total", value: "8" }] }, 1);
});

test("line chart rendering (one groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="bar" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["false", "true"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label"], {
        backgroundColor: "#a7d3f9",
        borderColor: "#4EA7F2",
        data: [5, 3],
        label: "Count",
    });
    checkLegend(view, "Count");
    checkTooltip(view, { lines: [{ label: "false", value: "5" }] }, 0);
    checkTooltip(view, { lines: [{ label: "true", value: "3" }] }, 1);
});

test("line chart rendering (two groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["false", "true"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#a7d3f9",
                borderColor: "#4EA7F2",
                data: [1, 3],
                label: "xphone",
            },
            {
                backgroundColor: "#f5b0ba",
                borderColor: "#EA6175",
                data: [4, 0],
                label: "xpad",
            },
        ]
    );
    checkLegend(view, ["xphone", "xpad"]);
    checkTooltip(
        view,
        {
            lines: [
                { label: "false / xpad", value: "4" },
                { label: "false / xphone", value: "1" },
            ],
        },
        0
    );
    checkTooltip(
        view,
        {
            lines: [
                { label: "true / xphone", value: "3" },
                { label: "true / xpad", value: "0" },
            ],
        },
        1
    );
});

test("line chart many2many groupBy", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="revenue" type="measure" />
                <field name="color_ids" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["black", "red"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label"], {
        backgroundColor: "#a7d3f9",
        borderColor: "#4EA7F2",
        data: [10, 13],
        label: "Revenue",
    });
    checkLegend(view, "Revenue");
    checkTooltip(view, { lines: [{ label: "black", value: "10" }], title: "Revenue" }, 0);
    checkTooltip(view, { lines: [{ label: "red", value: "13" }], title: "Revenue" }, 1);
});

test("Check if values in tooltip are correctly sorted when groupBy filter are applied", async () => {
    Foo._records = [
        { product_id: 100, foo: 1, revenue: 12 },
        { product_id: 100, foo: 2, revenue: 5 },
        { product_id: 100, foo: 3, revenue: 1.45e2 },
        { product_id: 100, foo: 4, revenue: -9 },
        { product_id: 200, foo: 5, revenue: 0 },
        { product_id: 200, foo: 6, revenue: -1 },
        { product_id: 200, foo: 7, revenue: Math.PI },
        { product_id: 200, foo: 8, revenue: 80.67 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: `
                <graph type="line" stacked="0">
                    <field name="revenue" type="measure"/>
                    <field name="product_id"/>
                    <field name="foo"/>
                </graph>
            `,
    });
    checkTooltip(
        view,
        {
            lines: [
                { label: "xphone / 3", value: "145.00" },
                { label: "xphone / 1", value: "12.00" },
                { label: "xphone / 2", value: "5.00" },
                { label: "xphone / 5", value: "0.00" },
                { label: "xphone / 6", value: "0.00" },
                { label: "xphone / 7", value: "0.00" },
                { label: "xphone / 8", value: "0.00" },
                { label: "xphone / 4", value: "-9.00" },
            ],
            title: "Revenue",
        },
        0
    );
    checkTooltip(
        view,
        {
            lines: [
                { label: "xpad / 8", value: "80.67" },
                { label: "xpad / 7", value: "3.14" },
                { label: "xpad / 1", value: "0.00" },
                { label: "xpad / 2", value: "0.00" },
                { label: "xpad / 3", value: "0.00" },
                { label: "xpad / 4", value: "0.00" },
                { label: "xpad / 5", value: "0.00" },
                { label: "xpad / 6", value: "-1.00" },
            ],
            title: "Revenue",
        },
        1
    );
});

test("format total in hh:mm when measure is unit_amount", async () => {
    Foo._fields.unit_amount = fields.Float({ string: "Unit Amount" });
    Foo._records = [{ id: 1, unit_amount: 8 }];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="unit_amount" type="measure" widget="float_time" />
            </graph>
        `,
    });

    const { measure, fieldAttrs } = getGraphModelMetaData(view);

    expect(".o_graph_view").toHaveClass("o_view_controller");
    expect("div.o_graph_canvas_container canvas").toHaveCount(1);
    expect(measure).toBe("unit_amount", { message: `the measure should be "unit_amount"` });
    checkLegend(view, "Unit Amount");
    checkLabels(view, ["Total"]);
    expect(fieldAttrs[measure].widget).toBe("float_time", {
        message: "should be a float_time widget",
    });
    checkYTicks(view, [
        "00:00",
        "01:00",
        "02:00",
        "03:00",
        "04:00",
        "05:00",
        "06:00",
        "07:00",
        "08:00",
    ]);
    checkTooltip(view, { title: "Unit Amount", lines: [{ label: "Total", value: "08:00" }] }, 0);
});

test("Stacked button visible in the line chart", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });
    const model = getGraphModel(view);

    await selectMode("line");

    checkModeIs(view, "line");
    expect(model.metaData.stacked).toBe(true, { message: "graph should be stacked." });
    expect(getScaleY(view).stacked).toBe(true, {
        message: "The y axes should have stacked property set to true",
    });
    expect(`button.o_graph_button[data-tooltip="Stacked"]`).toHaveCount(1);

    await contains(`button.o_graph_button[data-tooltip="Stacked"]`).click();

    expect(model.metaData.stacked).toBe(false, {
        message: "graph should be a classic line chart.",
    });
    expect(getScaleY(view).stacked).toBe(undefined, {
        message: "The y axes should have stacked property set to undefined",
    });
});

test("Stacked line prop click false", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    await contains(`button.o_graph_button[data-tooltip="Stacked"]`).click();

    expect(getGraphModel(view).metaData.stacked).toBe(false, {
        message: "graph should be a classic line chart.",
    });
    expect(!!getScaleY(view).stacked).toBe(false, {
        message:
            "the y axes should have a stacked property set to false since the stacked property in line chart is false.",
    });
    expect(getGraphRenderer(view).getElementOptions().line.fill).toBe(false, {
        message: "The fill property should be false since the stacked property is false.",
    });

    const expectedDatasets = [
        {
            backgroundColor: "#a7d3f9",
            borderColor: "#4EA7F2",
            originIndex: 0,
            pointBackgroundColor: "#4EA7F2",
        },
        {
            backgroundColor: "#f5b0ba",
            borderColor: "#EA6175",
            originIndex: 0,
            pointBackgroundColor: "#EA6175",
        },
    ];
    const keysToEvaluate = [
        "backgroundColor",
        "borderColor",
        "originIndex",
        "pointBackgroundColor",
    ];
    checkDatasets(view, keysToEvaluate, expectedDatasets);
});

test("Stacked prop and default line chart", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    expect(getGraphModel(view).metaData.mode).toBe("line", {
        message: "should be in line chart mode.",
    });
    expect(getGraphModel(view).metaData.stacked).toBe(true, {
        message: "should be stacked by default.",
    });

    expect(getScaleY(view).stacked).toBe(true, {
        message:
            "the stacked property in y axes should be true when the stacked is enabled in line chart",
    });
    expect(getGraphRenderer(view).getElementOptions().line.fill).toBe(true, {
        message: "The fill property should be true to add backgroundColor in line chart.",
    });

    const expectedDatasets = [];
    const keysToEvaluate = [
        "backgroundColor",
        "borderColor",
        "originIndex",
        "pointBackgroundColor",
    ];
    const datasets = getChart(view).data.datasets;
    const colors = getColors(undefined, "sm");
    for (let i = 0; i < datasets.length; i++) {
        const expectedColor = colors[i];
        expectedDatasets.push({
            backgroundColor: lightenColor(expectedColor, 0.5),
            borderColor: expectedColor,
            originIndex: 0,
            pointBackgroundColor: expectedColor,
        });
    }
    checkDatasets(view, keysToEvaluate, expectedDatasets);
});

test("Cumulative prop and default line chart", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    expect(getGraphModel(view).metaData.mode).toBe("line", {
        message: "should be in line chart mode.",
    });
    expect(getGraphModel(view).metaData.cumulated).toBe(false, {
        message: "should not be cumulative by default.",
    });

    await contains('[data-tooltip="Cumulative"]').click();

    expect(getGraphModel(view).metaData.cumulated).toBe(true, {
        message: "should be in cumulative",
    });
    const expectedDatasets = [
        {
            data: [1, 4],
        },
        {
            data: [4, 4],
        },
    ];
    checkDatasets(view, ["data"], expectedDatasets);
});

test("Default cumulative prop", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0" cumulated="1">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    expect(getGraphModel(view).metaData.mode).toBe("line", {
        message: "should be in line chart mode.",
    });
    expect(getGraphModel(view).metaData.cumulated).toBe(true, {
        message: "should be in cumulative",
    });
    expect(getGraphModel(view).metaData.cumulatedStart).toBe(false, {
        message: "should have cumulated start opted-out",
    });
});

test("Cumulative prop and cumulated start", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0" cumulated="1" cumulated_start="1">
                <field name="date" />
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="filter_after_march"
                    string="After March 2016"
                    domain="[['date', '>=', '2016-03-01']]"
                    />
            </search>
        `,
        context: {
            search_default_filter_after_march: 1,
        },
    });

    expect(getGraphModel(view).metaData.mode).toBe("line", {
        message: "should be in line chart mode",
    });
    expect(getGraphModel(view).metaData.cumulated).toBe(true, {
        message: "should be in cumulative",
    });
    expect(getGraphModel(view).metaData.cumulatedStart).toBe(true, {
        message: "should have cumulated start opted-in",
    });

    const expectedDatasets = [
        {
            data: [4, 4, 4],
        },
        {
            data: [0, 1, 2],
        },
    ];
    checkDatasets(view, ["data"], expectedDatasets);
});

test("line chart rendering (no groupBy, several domains)", async () => {
    const view = await mountView({
        resModel: "foo",
        type: "graph",
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="revenue" type="measure" />
            </graph>
        `,
        comparison: {
            domains: [
                { arrayRepr: [["bar", "=", true]], description: "True group" },
                { arrayRepr: [["bar", "=", false]], description: "False group" },
            ],
        },
    });

    checkLabels(view, ["", "Total", ""]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#a7d3f9",
                borderColor: "#4EA7F2",
                data: [undefined, 6],
                label: "True group",
            },
            {
                backgroundColor: "#f5b0ba",
                borderColor: "#EA6175",
                data: [undefined, 17],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["True group", "False group"]);
    checkTooltip(
        view,
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

test("line chart rendering (one groupBy, several domains)", async () => {
    Foo._records = [
        { bar: true, foo: 1, revenue: 14 },
        { bar: true, foo: 2, revenue: 0 },
        { bar: false, foo: 1, revenue: 12 },
        { bar: false, foo: 2, revenue: -4 },
        { bar: false, foo: 3, revenue: 2 },
        { bar: false, foo: 4, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="revenue" type="measure" />
                <field name="foo" />
            </graph>
        `,
        comparison: {
            domains: [
                { arrayRepr: [["bar", "=", true]], description: "True group" },
                { arrayRepr: [["bar", "=", false]], description: "False group" },
            ],
        },
    });

    checkLabels(view, ["1", "2", "3", "4"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#a7d3f9",
                borderColor: "#4EA7F2",
                data: [14, 0, 0, 0],
                label: "True group",
            },
            {
                backgroundColor: "#f5b0ba",
                borderColor: "#EA6175",
                data: [12, -4, 2, 0],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["True group", "False group"]);
    checkTooltip(
        view,
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
        view,
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
        view,
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
        view,
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

test("line chart rendering (one groupBy, several domains with date identification)", async () => {
    Foo._records = [
        { date: "2021-01-04", revenue: 12 },
        { date: "2021-01-12", revenue: 5 },
        { date: "2021-01-19", revenue: 15 },
        { date: "2021-01-26", revenue: 2 },
        { date: "2021-02-04", revenue: 14 },
        { date: "2021-02-17", revenue: 0 },
        { date: false, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="revenue" type="measure" />
                <field name="date" interval="week" />
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

    checkLabels(view, ["W05 2021", "W07 2021", "", ""]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#a7d3f9",
                borderColor: "#4EA7F2",
                data: [14, 0],
                label: "February 2021",
            },
            {
                backgroundColor: "#f5b0ba",
                borderColor: "#EA6175",
                data: [12, 5, 15, 2],
                label: "January 2021",
            },
        ]
    );
    checkLegend(view, ["February 2021", "January 2021"]);
    checkTooltip(
        view,
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
        view,
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
        view,
        {
            title: "Revenue",
            lines: [{ label: "W03 2021 / January 2021", value: "15" }],
        },
        2
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "W04 2021 / January 2021", value: "2" }],
        },
        3
    );
});

test("line chart rendering (one groupBy, several domains with date identification) without stacked attribute", async () => {
    Foo._records = [
        { date: "2021-01-04", revenue: 12 },
        { date: "2021-01-12", revenue: 5 },
        { date: "2021-01-19", revenue: 15 },
        { date: "2021-01-26", revenue: 2 },
        { date: "2021-02-04", revenue: 14 },
        { date: "2021-02-17", revenue: 0 },
        { date: false, revenue: 0 },
    ];

    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="revenue" type="measure" />
                <field name="date" interval="week" />
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

    expect(".o_graph_button[data-tooltip=Stacked]").not.toHaveClass("active", {
        message: "The stacked mode should be disabled",
    });
});

test("line chart rendering (two groupBy, several domains with no date identification)", async () => {
    Foo._records = [
        { date: "2021-01-04", bar: false, revenue: 12 },
        { date: "2021-01-12", bar: true, revenue: 5 },
        { date: "2021-02-04", bar: false, revenue: 14 },
        { date: "2021-02-17", bar: true, revenue: 0 },
        { date: false, bar: false, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="revenue" type="measure" />
                <field name="bar" />
                <field name="date" interval="week" />
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

    checkLabels(view, ["false", "true"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: "#a7d3f9",
                borderColor: "#4EA7F2",
                data: [14, 0],
                label: "February 2021 / W05 2021",
            },
            {
                backgroundColor: "#f5b0ba",
                borderColor: "#EA6175",
                data: [0, 0],
                label: "February 2021 / W07 2021",
            },
            {
                backgroundColor: "#a1e2d8",
                borderColor: "#43C5B1",
                data: [12, 0],
                label: "January 2021 / W01 2021",
            },
            {
                backgroundColor: "#fad1b0",
                borderColor: "#F4A261",
                data: [0, 5],
                label: "January 2021 / W02 2021",
            },
        ]
    );
    checkLegend(view, [
        "February 2021 / W05 2021",
        "February 2021 / W07 2021",
        "January 2021 / W01 2021",
        "January 2021 / W02 2021",
    ]);
    checkTooltip(
        view,
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
        view,
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
});

test("displaying line chart with only 1 data point", async () => {
    // this test makes sure the line chart does not crash when only one data
    // point is displayed.
    Foo._records = Foo._records.filter((id) => id === 1);

    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `<graph type="line" stacked="0" />`,
    });

    expect("canvas").toHaveCount(1);
});

test("pie chart rendering (no groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `<graph type="pie" />`,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(getGraphModelMetaData(view).mode).toBe("pie");
    checkLabels(view, ["Total"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label", "stack"], {
        backgroundColor: ["#4EA7F2"],
        borderColor: getBorderWhite(),
        data: [8],
        label: "",
        stack: undefined,
    });
    checkLegend(view, "Total");
    checkTooltip(view, { lines: [{ label: "Total", value: "8 (100.00%)" }] }, 0);
});

test("pie chart rendering (one groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="bar" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["false", "true"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data"], {
        backgroundColor: ["#4EA7F2", "#EA6175"],
        borderColor: getBorderWhite(),
        data: [5, 3],
    });
    checkLegend(view, ["false", "true"]);
    checkTooltip(view, { lines: [{ label: "false", value: "5 (62.50%)" }] }, 0);
    checkTooltip(view, { lines: [{ label: "true", value: "3 (37.50%)" }] }, 1);
});

test("pie chart many2many groupby", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="revenue" type="measure" />
                <field name="color_ids" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["black", "red", "None"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data"], {
        backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
        borderColor: getBorderWhite(),
        data: [10, 13, 8],
    });
    checkLegend(view, ["black", "red", "None"]);
    checkTooltip(view, { lines: [{ label: "black", value: "10 (32.26%)" }], title: "Revenue" }, 0);
    checkTooltip(view, { lines: [{ label: "red", value: "13 (41.94%)" }], title: "Revenue" }, 1);
    checkTooltip(view, { lines: [{ label: "None", value: "8 (25.81%)" }], title: "Revenue" }, 2);
});

test("pie chart rendering (two groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="bar" />
                <field name="product_id" />
            </graph>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    checkLabels(view, ["false / xphone", "false / xpad", "true / xphone"]);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label"], {
        backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
        borderColor: getBorderWhite(),
        data: [1, 4, 3],
        label: "",
    });
    checkLegend(view, ["false / xphone", "false / xpad", "true / xphone"]);
    checkTooltip(view, { lines: [{ label: "false / xphone", value: "1 (12.50%)" }] }, 0);
    checkTooltip(view, { lines: [{ label: "false / xpad", value: "4 (50.00%)" }] }, 1);
    checkTooltip(view, { lines: [{ label: "true / xphone", value: "3 (37.50%)" }] }, 2);
});

test("pie chart rendering (no groupBy, several domains)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="revenue" type="measure" />
            </graph>
        `,
        comparison: {
            domains: [
                { arrayRepr: [["bar", "=", true]], description: "True group" },
                { arrayRepr: [["bar", "=", false]], description: "False group" },
            ],
        },
    });

    checkLabels(view, ["Total"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: ["#4EA7F2"],
                borderColor: getBorderWhite(),
                data: [6],
                label: "True group",
            },
            {
                backgroundColor: ["#4EA7F2"],
                borderColor: getBorderWhite(),
                data: [17],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["Total"]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "True group / Total", value: "6 (100.00%)" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "False group / Total", value: "17 (100.00%)" }],
        },
        0,
        1
    );
});

test("pie chart rendering (one groupBy, several domains)", async () => {
    Foo._records = [
        { bar: true, foo: 1, revenue: 14 },
        { bar: true, foo: 2, revenue: 0 },
        { bar: false, foo: 1, revenue: 12 },
        { bar: false, foo: 2, revenue: 5 },
        { bar: false, foo: 3, revenue: 0 },
        { bar: false, foo: 4, revenue: 2 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="revenue" type="measure" />
                <field name="foo" />
            </graph>
        `,
        comparison: {
            domains: [
                { arrayRepr: [["bar", "=", true]], description: "True group" },
                { arrayRepr: [["bar", "=", false]], description: "False group" },
            ],
        },
    });

    checkLabels(view, ["1", "2", "4"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
                borderColor: getBorderWhite(),
                data: [14, 0, 0],
                label: "True group",
            },
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
                borderColor: getBorderWhite(),
                data: [12, 5, 2],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["1", "2", "4"]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "True group / 1", value: "14 (100.00%)" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "False group / 1", value: "12 (63.16%)" }],
        },
        0,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "False group / 2", value: "5 (26.32%)" }],
        },
        1,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "False group / 4", value: "2 (10.53%)" }],
        },
        2,
        1
    );
});

test("pie chart rendering (one groupBy, several domains with date identification)", async () => {
    Foo._records = [
        { date: "2021-01-04" },
        { date: "2021-01-12" },
        { date: "2021-01-19" },
        { date: "2021-01-26" },
        { date: "2021-02-04" },
        { date: "2021-02-17" },
        { date: false },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="date" interval="week" />
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

    checkLabels(view, ["W05 2021, W01 2021", "W07 2021, W02 2021", "W03 2021", "W04 2021"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1", "#F4A261"],
                borderColor: getBorderWhite(),
                data: [1, 1, 0, 0],
                label: "February 2021",
            },
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1", "#F4A261"],
                borderColor: getBorderWhite(),
                data: [1, 1, 1, 1],
                label: "January 2021",
            },
        ]
    );
    checkLegend(view, ["W05 2021, W01 2021", "W07 2021, W02 2021", "W03 2021", "W04 2021"]);
    checkTooltip(
        view,
        {
            lines: [{ label: "February 2021 / W05 2021", value: "1 (50.00%)" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            lines: [{ label: "January 2021 / W01 2021", value: "1 (25.00%)" }],
        },
        0,
        1
    );
    checkTooltip(
        view,
        {
            lines: [{ label: "February 2021 / W07 2021", value: "1 (50.00%)" }],
        },
        1,
        0
    );
    checkTooltip(
        view,
        {
            lines: [{ label: "January 2021 / W02 2021", value: "1 (25.00%)" }],
        },
        1,
        1
    );
    checkTooltip(
        view,
        {
            lines: [{ label: "January 2021 / W03 2021", value: "1 (25.00%)" }],
        },
        2,
        1
    );
    checkTooltip(
        view,
        {
            lines: [{ label: "January 2021 / W04 2021", value: "1 (25.00%)" }],
        },
        3,
        1
    );
});

test("pie chart rendering (two groupBy, several domains with no date identification)", async () => {
    Foo._records = [
        { date: "2021-01-04", bar: false, revenue: 12 },
        { date: "2021-01-12", bar: true, revenue: 5 },
        { date: "2021-02-04", bar: false, revenue: 14 },
        { date: "2021-02-17", bar: true, revenue: 0 },
        { date: false, bar: false, revenue: 0 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="revenue" type="measure" />
                <field name="bar" />
                <field name="date" interval="week" />
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

    checkLabels(view, ["false / W05 2021", "false / W01 2021", "true / W02 2021"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
                borderColor: getBorderWhite(),
                data: [14, 0, 0],
                label: "February 2021",
            },
            {
                backgroundColor: ["#4EA7F2", "#EA6175", "#43C5B1"],
                borderColor: getBorderWhite(),
                data: [0, 12, 5],
                label: "January 2021",
            },
        ]
    );
    checkLegend(view, ["false / W05 2021", "false / W01 2021", "true / W02 2021"]);
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "February 2021 / false / W05 2021", value: "14 (100.00%)" }],
        },
        0,
        0
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "January 2021 / false / W01 2021", value: "12 (70.59%)" }],
        },
        1,
        1
    );
    checkTooltip(
        view,
        {
            title: "Revenue",
            lines: [{ label: "January 2021 / true / W02 2021", value: "5 (29.41%)" }],
        },
        2,
        1
    );
});

test("pie chart rendering (no data)", async () => {
    Foo._records = [];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `<graph type="pie" />`,
    });

    checkLabels(view, ["No data"]);
    checkDatasets(
        view,
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
    checkLegend(view, ["No data"]);
    checkTooltip(view, { lines: [{ label: "No data", value: "0 (100.00%)" }] }, 0);
});

test("pie chart rendering (no data, several domains)", async () => {
    Foo._records = [{ product_id: 100, bar: true }];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="product_id" />
            </graph>
        `,
        comparison: {
            domains: [
                { arrayRepr: [["bar", "=", true]], description: "True group" },
                { arrayRepr: [["bar", "=", false]], description: "False group" },
            ],
        },
    });

    checkLabels(view, ["xphone", "No data"]);
    checkDatasets(
        view,
        ["backgroundColor", "borderColor", "data", "label"],
        [
            {
                backgroundColor: ["#4EA7F2"],
                borderColor: getBorderWhite(),
                data: [1],
                label: "True group",
            },
            {
                backgroundColor: ["#4EA7F2", DEFAULT_BG],
                borderColor: getBorderWhite(),
                data: [undefined, 1],
                label: "False group",
            },
        ]
    );
    checkLegend(view, ["xphone", "No data"]);
    checkTooltip(view, { lines: [{ label: "True group / xphone", value: "1 (100.00%)" }] }, 0, 0);
    checkTooltip(view, { lines: [{ label: "False group / No data", value: "0 (100.00%)" }] }, 1, 1);
});

test("pie chart rendering (mix of positive and negative values)", async () => {
    Foo._records = [
        { bar: true, revenue: 2 },
        { bar: false, revenue: -3 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="pie">
                <field name="revenue" type="measure" />
                <field name="bar" />
            </graph>
        `,
    });

    expect(".o_view_nocontent").toHaveCount(0);
    expect(".o_graph_canvas_container").toHaveCount(1);
    checkDatasets(view, ["backgroundColor", "borderColor", "data", "label", "stack"], {
        backgroundColor: ["#4EA7F2"],
        borderColor: getBorderWhite(),
        data: [2],
        label: "",
        stack: undefined,
    });
});

test("pie chart toggling dataset hides label", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: `<graph type="pie"/>`,
    });
    checkLabels(view, ["Total"]);
    await clickOnLegend(view, "Total");
    expect(getChart(view).legend.legendItems[0].hidden).toBe(true);
});

test("mode props", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `<graph type="pie" />`,
    });

    expect(getGraphModelMetaData(view).mode).toBe("pie", {
        message: "should be in pie chart mode",
    });
    expect(getChart(view).config.type).toBe("pie");
});

test("field id not in groupBy", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="id" />
            </graph>
        `,
    });

    checkLabels(view, ["Total"]);
    checkDatasets(view, ["backgroundColor", "data", "label", "originIndex", "stack"], {
        backgroundColor: "#4EA7F2",
        data: [8],
        label: "Count",
        originIndex: 0,
        stack: "",
    });
    checkLegend(view, "Count");
});

test("props modifications", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="bar" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }" />
            </search>
        `,
    });

    checkModeIs(view, "bar");
    expect(getYAxisLabel(view)).toBe("Count");

    await selectMode("line");

    checkModeIs(view, "line");

    await toggleMenu("Measures");
    await toggleMenuItem("Revenue");

    expect(getYAxisLabel(view)).toBe("Revenue");

    await toggleSearchBarMenu();
    await toggleMenuItem("Color");

    checkModeIs(view, "line");
    expect(getYAxisLabel(view)).toBe("Revenue");
});

test("switching mode", async () => {
    const view = await mountView({ type: "graph", resModel: "foo" });

    checkModeIs(view, "bar");

    await selectMode("bar"); // click on the active mode does not change anything

    checkModeIs(view, "bar");

    await selectMode("line");

    checkModeIs(view, "line");

    await selectMode("pie");

    checkModeIs(view, "pie");
});

test("switching measure", async () => {
    const checkMeasure = (measure) => {
        const yAxe = getChart(view).config.options.scales.y;
        expect(yAxe.title.text).toBe(measure);
        expect(`.o_menu_item:contains(${measure})`).toHaveClass("selected");
    };

    const view = await mountView({ type: "graph", resModel: "foo" });

    await toggleMenu("Measures");

    checkMeasure("Count");
    checkLegend(view, "Count");

    await toggleMenuItem("Foo");

    checkMeasure("Foo");
    checkLegend(view, "Foo");
});

test("process default view description", async () => {
    expect(new GraphArchParser().parse()).toEqual({
        fields: {},
        fieldAttrs: {},
        groupBy: [],
        measures: [],
    });
});

test("process simple arch (no field tag)", async () => {
    const { env } = await makeMockServer();
    const fooFields = env["foo"]._fields;

    const arch1 = /* xml */ `
        <graph order="ASC" disable_linking="1" type="line" />
    `;

    expect(new GraphArchParser().parse(arch1, fooFields)).toEqual({
        disableLinking: true,
        fields: fooFields,
        fieldAttrs: {},
        groupBy: [],
        measures: [],
        mode: "line",
        order: "ASC",
    });

    const arch2 = /* xml */ `
        <graph disable_linking="0" string="Title" stacked="False" />
    `;

    expect(new GraphArchParser().parse(arch2, fooFields)).toEqual({
        disableLinking: false,
        fields: fooFields,
        fieldAttrs: {},
        groupBy: [],
        measures: [],
        stacked: false,
        title: "Title",
    });
});

test("process arch with field tags", async () => {
    Foo._fields.fighters = fields.Text();

    const { env } = await makeMockServer();
    const fooFields = env["foo"]._fields;

    const arch = /* xml */ `
        <graph type="pie">
            <field name="revenue" type="measure" />
            <field name="date" interval="day" />
            <field name="foo" invisible="False" />
            <field name="bar" invisible="True" string="My invisible field" />
            <field name="id" />
            <field name="fighters" string="FooFighters" />
        </graph>
    `;

    expect(new GraphArchParser().parse(arch, fooFields)).toEqual({
        fields: fooFields,
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

test("process arch with non stored field tags of type measure", async () => {
    Foo._fields.revenue.store = false;

    const { env } = await makeMockServer();
    const fooFields = env["foo"]._fields;
    const arch = `
        <graph>
            <field name="product_id"/>
            <field name="revenue" type="measure"/>
            <field name="foo" type="measure"/>
        </graph>
    `;
    expect(new GraphArchParser().parse(arch, fooFields)).toEqual({
        fields: fooFields,
        fieldAttrs: {},
        measure: "foo",
        measures: ["revenue", "foo"],
        groupBy: ["product_id"],
    });
});

test("displaying chart data with three groupbys", async () => {
    // this test makes sure the line chart shows all data labels (X axis) when
    // it is grouped by several fields
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="bar">
                <field name="product_id" />
                <field name="bar" />
                <field name="color_id" />
            </graph>
        `,
    });

    checkLabels(view, ["xphone", "xpad"]);
    checkLegend(view, ["false / None", "true / red", "true / None", "Sum"]);

    await selectMode("line");

    checkLabels(view, ["xphone", "xpad"]);
    checkLegend(view, ["false / None", "true / red", "true / None"]);

    await selectMode("pie");

    checkLabels(view, [
        "xphone / false / None",
        "xphone / true / red",
        "xphone / true / None",
        "xpad / false / None",
    ]);
    checkLegend(view, [
        "xphone / false / None",
        "xphone / true / red",
        "xphone / true / None",
        "xpad / false / None",
    ]);
});

test("no content helper", async () => {
    Foo._records = [];

    await mountView({
        type: "graph",
        resModel: "foo",
        noContentHelp: /* xml */ `
            <p class="abc">This helper should not be displayed in graph views</p>
        `,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(".abc").toHaveCount(0);
});

test("no content helper after update", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        noContentHelp: /* xml */ `
            <p class="abc">This helper should not be displayed in graph views</p>
        `,
        config: {
            views: [[false, "search"]],
        },
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(".abc").toHaveCount(0);

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");

    expect(".o_graph_canvas_container canvas").toHaveCount(1);
    expect(".o_view_nocontent").toHaveCount(0);
    expect(".abc").toHaveCount(0);
});

test("can reload with other group by", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }" />
            </search>
        `,
    });

    checkLabels(view, ["xphone", "xpad"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Color");

    checkLabels(view, ["red", "None"]);
});

test("save params succeeds", async () => {
    expect.assertions(4);

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
    onRpc("create_or_replace", ({ args }) => {
        expect(args[0].context).toEqual(expectedContexts.shift());
        return serverId++;
    });

    await mountView({
        resModel: "foo",
        type: "graph",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
            </graph>
        `,
        searchViewId: false,
        searchViewArch: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]" />
                <filter name="filter_with_context"
                    string="Filter With Context"
                    domain="[]"
                    context="{ 'graph_measure': 'foo', 'graph_mode': 'line', 'graph_groupbys': ['color_id'] }"
                    />
                <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }" />
                <filter name="group_by_product" string="Product" context="{ 'group_by': 'product_id' }" />
            </search>
        `,
    });

    await toggleSaveFavorite();
    await editFavoriteName("First Favorite");
    await saveFavorite();

    await toggleMenu("Measures");
    await toggleMenuItem("Foo");

    await toggleSaveFavorite();
    await editFavoriteName("Second Favorite");
    await saveFavorite();

    await selectMode("line");

    await toggleSaveFavorite();
    await editFavoriteName("Third Favorite");
    await saveFavorite();

    await toggleMenuItem("Product");
    await toggleMenuItem("Color");

    await editFavoriteName("Fourth Favorite");
    await saveFavorite();
});

test("correctly uses graph_ keys from the context", async () => {
    Foo._records.at(-1).color_id = 1;

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
            </graph>
        `,
        context: {
            graph_measure: "foo",
            graph_mode: "line",
            graph_groupbys: ["color_id"],
        },
    });

    checkLabels(view, ["black", "red"]);
    checkLegend(view, "Foo");
    checkModeIs(view, "line");
    expect(getYAxisLabel(view)).toBe("Foo");
    expect(getGraphModelMetaData(view).mode).toBe("line");
});

test("correctly uses graph_ keys from the context (at reload)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="context" domain="[]" string="Context" context="{ 'graph_measure': 'foo', 'graph_mode': 'line' }" />
            </search>
        `,
    });

    checkLegend(view, "Count");
    expect(getYAxisLabel(view)).toBe("Count");
    checkModeIs(view, "bar");

    await toggleSearchBarMenu();
    await toggleMenuItem("Context");

    checkLegend(view, "Foo");
    expect(getYAxisLabel(view)).toBe("Foo");
    checkModeIs(view, "line");
});

test("correctly use group_by key from the context", async () => {
    Foo._records.at(-1).color_id = 1;

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
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

    checkLabels(view, ["black", "red"]);
    checkLegend(view, "Foo");
    checkModeIs(view, "line");
    expect(getYAxisLabel(view)).toBe("Foo");
    expect(getGraphModelMetaData(view).mode).toBe("line");
});

test("an invisible field should not be used as groupBy", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="foo" invisible="1" />
            </graph>
        `,
    });

    checkLabels(view, ["Total"]);
});

test("format values as float in case at least one value is not an number", async () => {
    Foo._records = [
        { bar: false, revenue: 1.5 },
        { bar: true, revenue: 2 },
    ];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
                <field name="bar" />
            </graph>
        `,
    });

    checkDatasets(view, "data", { data: [1.5, 2] });
    checkLabels(view, ["false", "true"]);
    checkTooltip(view, { title: "Revenue", lines: [{ label: "false", value: "1.50" }] }, 0);
    checkTooltip(view, { title: "Revenue", lines: [{ label: "true", value: "2.00" }] }, 1);
});

test("the active measure description is the arch string attribute in priority", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" string="Nirvana" />
                <field name="foo" type="measure" string="FooFighters" />
            </graph>
        `,
    });

    checkTooltip(view, { title: "FooFighters", lines: [{ label: "Total", value: "239" }] }, 0);

    await toggleMenu("Measures");
    await toggleMenuItem("Nirvana");

    checkTooltip(view, { title: "Nirvana", lines: [{ label: "Total", value: "23" }] }, 0);
});

test("reload graph with correct fields", async () => {
    expect.assertions(2);

    onRpc("web_read_group", ({ kwargs }) => {
        expect(kwargs.fields).toEqual(["__count", "foo:sum"]);
    });

    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="foo" type="measure" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]" />
            </search>
        `,
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");
});

test("initial groupby is kept when reloading", async () => {
    expect.assertions(7);

    onRpc("web_read_group", ({ kwargs }) => {
        expect(kwargs.groupby).toEqual(["product_id"]);
    });
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
                <field name="foo" type="measure" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]" />
            </search>
        `,
    });

    checkLabels(view, ["xphone", "xpad"]);
    checkLegend(view, "Foo");
    checkDatasets(view, "data", { data: [82, 157] });
    expect(getYAxisLabel(view)).toBe("Foo");

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");
    expect(".o_graph_canvas_container").toHaveCount(0);
});

test("use a many2one as a measure should work (without groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" type="measure" />
            </graph>
        `,
    });

    checkLabels(view, ["Total"]);
    checkLegend(view, "Product");
    checkDatasets(view, "data", { data: [2] });
    expect(getYAxisLabel(view)).toBe("Product");
});

test("use a many2one as a measure should work (with groupBy)", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="bar" />
                <field name="product_id" type="measure" />
            </graph>
        `,
    });

    checkLabels(view, ["false", "true"]);
    checkLegend(view, "Product");
    checkDatasets(view, "data", { data: [2, 1] });
});

test("use a many2one as a measure and as a groupby should work", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" type="measure" />
                <field name="product_id" />
            </graph>
        `,
    });

    checkLabels(view, ["xphone", "xpad"]);
    checkLegend(view, "Product");
    checkDatasets(view, "data", { data: [1, 1] });
    expect(getYAxisLabel(view)).toBe("Product");
});

test("differentiate many2one values with same label", async () => {
    Product._records.push({ id: 300, name: "xphone" });
    Foo._records.push({ product_id: 300 });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
            </graph>
        `,
    });

    checkLabels(view, ["xphone", "xpad", "xphone (2)"]);
});

test("not use a many2one as a measure by default", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        viewId: false,
    });

    await toggleMenu("Measures");

    expect(queryAllTexts(".o-dropdown--menu .o_menu_item")).toEqual(["Foo", "Revenue", "Count"]);
});

test.tags("desktop");
test("graph view crash when moving from search view using Down key", async () => {
    await mountView({ type: "graph", resModel: "foo" });

    await contains(".o_searchview input").press("ArrowDown");

    expect(".o_graph_view").toHaveCount(1);
});

test("graph measures should be alphabetically sorted (exception: 'Count' is last)", async () => {
    Foo._fields.bouh = fields.Integer();

    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="foo" type="measure" />
                <field name="bouh" type="measure" />
            </graph>
        `,
    });

    await toggleMenu("Measures");

    expect(queryAllTexts(".o-dropdown--menu .o_menu_item")).toEqual([
        "Bouh",
        "Foo",
        "Revenue",
        "Count",
    ]);
});

test("a many2one field can be added as measure in arch", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" type="measure" />
            </graph>
        `,
    });

    checkLegend(view, "Product");
    expect(getYAxisLabel(view)).toBe("Product");
});

test("non store fields defined on the arch are present in the measures", async () => {
    Foo._fields.revenue.store = false;
    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id"/>
                <field name="revenue" type="measure"/>
                <field name="foo" type="measure"/>
            </graph>
        `,
    });

    await toggleMenu("Measures");
    expect(queryAllTexts(`.o_menu_item`)).toEqual(["Foo", "Revenue", "Count"]);
});

test("graph view `graph_measure` field in context", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        viewId: false,
        context: {
            graph_measure: "product_id",
        },
    });

    expect(getYAxisLabel(view)).toBe("Product");
    checkLegend(view, "Product");
    checkTooltip(view, { title: "Product", lines: [{ label: "Total", value: "2" }] }, 0);
});

test("`graph_measure` in context is prefered to measure in arch", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" type="measure" />
            </graph>
        `,
        context: {
            graph_measure: "product_id",
        },
    });

    expect(getYAxisLabel(view)).toBe("Product");
    checkLegend(view, "Product");
    checkTooltip(view, { title: "Product", lines: [{ label: "Total", value: "2" }] }, 0);
});

test("None should appear in bar, pie graph but not in line graph with multiple groupbys", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="date" />
                <field name="color_id" />
            </graph>
        `,
    });
    const someNone = () => getChart(view).data.labels.some((l) => /none/i.test(l));

    expect(someNone()).toBe(false);

    await selectMode("bar");

    expect(someNone()).toBe(true);

    await selectMode("pie");

    expect(someNone()).toBe(true);

    // None should not appear after switching back to line chart
    await selectMode("line");

    expect(someNone()).toBe(false);
});

test("an invisible field can not be found in the 'Measures' menu", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" invisible="1" />
            </graph>
        `,
    });

    checkTooltip(view, { lines: [{ label: "Total", value: "8" }] }, 0);

    await toggleMenu("Measures");

    expect(".o_menu_item:contains(Revenue)").toHaveCount(0, {
        message: `"Revenue" can not be found in the "Measures" menu`,
    });
});

test("graph view only keeps finer groupby filter option for a given groupby", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        groupBy: ["date:year", "product_id", "date", "date:quarter"],
        arch: /* xml */ `<graph type="line" />`,
    });

    checkLabels(view, ["January 2016", "March 2016", "April 2016", "May 2016"]);
    checkLegend(view, ["xphone", "xpad"]);
    checkDatasets(
        view,
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
});

test("action name is displayed in breadcrumbs", async () => {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Glou glou",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [[false, "graph"]],
    });
    expect(".o_breadcrumb .active:first").toHaveText("Glou glou");
});

test("clicking on bar charts triggers a do_action", async () => {
    expect.assertions(6);

    mockService("action", {
        doAction(actionRequest, options) {
            expect(actionRequest).toEqual({
                context: { allowed_company_ids: [1], lang: "en", tz: "taht", uid: 7 },
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
            expect(options).toEqual({ viewType: "list" });
        },
    });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph string="Foo Analysis">
                <field name="bar" />
            </graph>
        `,
    });

    checkModeIs(view, "bar");
    checkDatasets(view, ["domains"], {
        domains: [[["bar", "=", false]], [["bar", "=", true]]],
    });

    await clickOnDataset(view);
});

test("Clicking on bar charts removes group_by and search_default_* context keys", async () => {
    expect.assertions(2);

    mockService("action", {
        doAction(actionRequest, options) {
            expect(actionRequest).toEqual({
                context: { allowed_company_ids: [1], lang: "en", tz: "taht", uid: 7 },
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
            expect(options).toEqual({ viewType: "list" });
        },
    });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph string="Foo Analysis">
                <field name="bar" />
            </graph>
        `,
        context: {
            search_default_user: 1,
            group_by: "bar",
        },
    });

    await clickOnDataset(view);
});

test("clicking on a pie chart trigger a do_action with correct views", async () => {
    expect.assertions(6);

    Foo._views[["list", 364]] = /* xml */ `<list />`;
    Foo._views[["form", 29]] = /* xml */ `<form />`;

    mockService("action", {
        doAction(actionRequest, options) {
            expect(actionRequest).toEqual({
                context: { allowed_company_ids: [1], lang: "en", tz: "taht", uid: 7 },
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
            expect(options).toEqual({ viewType: "list" });
        },
    });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph string="Foo Analysis" type="pie">
                <field name="bar" />
            </graph>
        `,
        config: {
            views: [
                [364, "list"],
                [29, "form"],
            ],
        },
    });

    checkModeIs(view, "pie");
    checkDatasets(view, ["domains"], {
        domains: [[["bar", "=", false]], [["bar", "=", true]]],
    });

    await clickOnDataset(view);
});

test('graph view with attribute disable_linking="1"', async () => {
    mockService("action", {
        doAction() {
            throw new Error("should not perform a `doAction`");
        },
    });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph disable_linking="1">
                <field name="bar" />
            </graph>
        `,
    });

    checkModeIs(view, "bar");
    checkDatasets(view, ["domains"], {
        domains: [[["bar", "=", false]], [["bar", "=", true]]],
    });

    await clickOnDataset(view);
});

test("graph view without invisible attribute on field", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
    });
    await toggleMenu("Measures");

    expect(".o_menu_item").toHaveCount(3, {
        message:
            "there should be three menu items in the measures dropdown (count, revenue and foo)",
    });
    expect(".o_menu_item:contains(Revenue)").toHaveCount(1);
    expect(".o_menu_item:contains(Foo)").toHaveCount(1);
    expect(".o_menu_item:contains(Count)").toHaveCount(1);
});

test("graph view with invisible attribute on field", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="revenue" invisible="1" />
            </graph>
        `,
    });
    await toggleMenu("Measures");

    expect(".o_menu_item").toHaveCount(2, {
        message: "there should be only two menu items in the measures dropdown (count and foo)",
    });
    expect(".o_menu_item:contains(Revenue)").toHaveCount(0);
});

test("graph view sort by measure", async () => {
    // change last record from foo as there are 4 records count for each product
    Product._records.push({ id: 150, name: "zphone" });
    Foo._records.at(-1).product_id = 150;

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph order="DESC">
                <field name="product_id" />
            </graph>
        `,
    });

    expect(".fa-sort-amount-asc").toHaveCount(1);
    expect(".fa-sort-amount-desc").toHaveCount(1);

    checkLegend(view, "Count", "measure should be by count");
    expect(".fa-sort-amount-desc").toHaveClass("active");
    checkDatasets(view, "data", { data: [4, 3, 1] });

    await clickSort("asc");

    expect(".fa-sort-amount-asc").toHaveClass("active");
    checkDatasets(view, "data", { data: [1, 3, 4] });

    await clickSort("desc");

    expect(".fa-sort-amount-desc").toHaveClass("active");
    checkDatasets(view, "data", { data: [4, 3, 1] });

    // again click on descending button to deactivate order
    await clickSort("desc");

    expect(".fa-sort-amount-desc").not.toHaveClass("active");
    checkDatasets(view, "data", { data: [4, 1, 3] });

    // set line mode
    await selectMode("line");
    expect(".fa-sort-amount-asc").toHaveCount(1);
    expect(".fa-sort-amount-desc").toHaveCount(1);

    checkLegend(view, "Count", "measure should be by count");
    expect(".fa-sort-amount-desc").not.toHaveClass("active");
    checkDatasets(view, "data", { data: [4, 1, 3] });

    await clickSort("asc");

    expect(".fa-sort-amount-asc").toHaveClass("active");
    checkDatasets(view, "data", { data: [1, 3, 4] });

    await clickSort("desc");

    expect(".fa-sort-amount-desc").toHaveClass("active");
    checkDatasets(view, "data", { data: [4, 3, 1] });
});

test("graph view sort by measure for grouped data", async () => {
    // change last record from foo as there are 4 records count for each product
    Product._records.push({ id: 150, name: "zphone" });
    Foo._records.at(-1).product_id = 150;

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" />
                <field name="bar" />
            </graph>
        `,
    });

    checkLegend(view, ["false", "true", "Sum"], "measure should be by count");
    checkDatasets(view, "data", [{ data: [1, 1, 3] }, { data: [3, 0, 0] }, { data: [4, 1, 3] }]);

    await clickSort("asc");

    expect(".fa-sort-amount-asc").toHaveClass("active");
    checkDatasets(view, "data", [{ data: [1, 3, 1] }, { data: [0, 0, 3] }, { data: [1, 3, 4] }]);

    await clickSort("desc");

    expect(".fa-sort-amount-desc").toHaveClass("active");
    checkDatasets(view, "data", [{ data: [1, 3, 1] }, { data: [3, 0, 0] }, { data: [4, 3, 1] }]);

    // again click on descending button to deactivate order
    await clickSort("desc");

    expect(".fa-sort-amount-desc").not.toHaveClass("active");
    checkDatasets(view, "data", [{ data: [1, 1, 3] }, { data: [3, 0, 0] }, { data: [4, 1, 3] }]);
});

test("graph view sort by measure for multiple grouped data", async () => {
    // change last record from foo as there are 4 records count for each product
    Product._records.push({ id: 150, name: "zphone" });
    Foo._records.at(-1).product_id = 150;
    Foo._records.splice(
        0,
        4,
        { id: 1, foo: 48, bar: false, product_id: 200, date: "2016-04-01" },
        { id: 2, foo: 49, bar: false, product_id: 200, date: "2016-04-01" },
        { id: 3, foo: 50, bar: true, product_id: 100, date: "2016-01-03" },
        { id: 4, foo: 50, bar: true, product_id: 200, date: "2016-01-03" }
    );

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="date" />
                <field name="product_id" />
            </graph>
        `,
    });

    checkLegend(view, ["xphone", "xpad", "zphone", "Sum"], "measure should be by count");
    checkDatasets(view, "data", [
        { data: [1, 0, 0, 0] },
        { data: [1, 2, 1, 2] },
        { data: [0, 1, 0, 0] },
        { data: [2, 3, 1, 2] },
    ]);

    await clickSort("asc");

    expect(".fa-sort-amount-asc").toHaveClass("active");
    checkDatasets(view, "data", [
        { data: [1, 1, 2, 2] },
        { data: [0, 1, 0, 0] },
        { data: [0, 0, 0, 1] },
        { data: [1, 2, 2, 3] },
    ]);

    await clickSort("desc");

    expect(".fa-sort-amount-desc").toHaveClass("active");
    checkDatasets(view, "data", [
        { data: [1, 0, 0, 0] },
        { data: [2, 1, 2, 1] },
        { data: [0, 1, 0, 0] },
        { data: [3, 2, 2, 1] },
    ]);

    // again click on descending button to deactivate order
    await clickSort("desc");

    expect(".fa-sort-amount-desc").not.toHaveClass("active");
    checkDatasets(view, "data", [
        { data: [1, 0, 0, 0] },
        { data: [1, 2, 1, 2] },
        { data: [0, 1, 0, 0] },
        { data: [2, 3, 1, 2] },
    ]);
});

test("empty graph view with sample data", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph sample="1">
                <field name="product_id" />
                <field name="date" />
            </graph>
        `,
        context: {
            search_default_false_domain: 1,
        },
        searchViewArch: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]" />
            </search>
        `,
        noContentHelp: /* xml */ `<p class="abc">click to add a foo</p>`,
    });

    expect(".o_graph_view .o_content").toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(1);
    expect(".o_graph_canvas_container canvas").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");

    expect(".o_graph_view .o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(0);
    expect(".o_graph_canvas_container canvas").toHaveCount(1);
});

test("non empty graph view with sample data", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph sample="1">
                <field name="product_id" />
                <field name="date" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="false_domain" string="False Domain" domain="[(0, '=', 1)]" />
            </search>
        `,
        noContentHelp: /* xml */ `<p class="abc">click to add a foo</p>`,
    });

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_view_nocontent").toHaveCount(0);
    expect(".o_graph_canvas_container canvas").toHaveCount(1);

    await toggleSearchBarMenu();
    await toggleMenuItem("False Domain");

    expect(".o_content").not.toHaveClass("o_view_sample_data");
    expect(".o_graph_canvas_container canvas").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(1);
});

test("empty graph view without sample data after filter", async () => {
    await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="date" />
            </graph>
        `,
        domain: Domain.FALSE.toList(),
        noContentHelp: /* xml */ `<p class="abc">click to add a foo</p>`,
    });

    expect(".o_graph_canvas_container canvas").toHaveCount(0);
    expect(".o_view_nocontent").toHaveCount(1);
});

test.tags("desktop");
test("reload chart with switchView button keep internal state", async () => {
    Foo._views.list = /* xml */ `<list />`;

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Foo Action 1",
        res_model: "foo",
        type: "ir.actions.act_window",
        views: [
            [false, "graph"],
            [false, "list"],
        ],
    });

    expect(getModeButton("bar")).toHaveClass("active");

    await selectMode("line");

    expect(getModeButton("line")).toHaveClass("active");

    await switchView("graph");

    expect(getModeButton("line")).toHaveClass("active");
});

test("fallback on initial groupby when the groupby from control panel has 0 length", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="group_by_foo" string="Foo" domain="[]" context="{ 'group_by': 'foo'}" />
            </search>
        `,
        context: {
            search_default_group_by_foo: 1,
        },
    });

    checkLabels(view, ["2", "3", "4", "24", "42", "48", "53", "63"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("Foo");

    checkLabels(view, ["xphone", "xpad"]);
});

test("change mode, stacked, or order via the graph buttons does not reload datapoints, change measure does", async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step(kwargs.fields);
    });
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="product_id" />
            </graph>
        `,
    });

    checkModeIs(view, "line");

    await selectMode("bar");

    checkModeIs(view, "bar");
    expect(`[data-tooltip="Stacked"]`).toHaveClass("active");

    await contains(`[data-tooltip="Stacked"]`).click();

    expect(`[data-tooltip="Stacked"]`).not.toHaveClass("active");
    expect(`[data-tooltip="Ascending"]`).not.toHaveClass("active");

    await contains(`[data-tooltip="Ascending"]`).click();

    expect(`[data-tooltip="Ascending"]`).toHaveClass("active");

    await toggleMenu("Measures");
    await toggleMenuItem("Foo");

    expect.verifySteps([
        ["__count"], // first load
        ["__count", "foo:sum"], // reload due to change in measure
    ]);
});

test("concurrent reloads: add a filter, and directly toggle a measure", async () => {
    let def;
    onRpc("web_read_group", () => def);
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="my_filter" string="My Filter" domain="[('id', '&lt;', 6)]" />
            </search>
        `,
    });

    checkDatasets(view, ["data", "label"], {
        data: [4, 4],
        label: "Count",
    });

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");

    checkDatasets(view, ["data", "label"], {
        data: [4, 4],
        label: "Count",
    });

    // Toggle a measure
    await toggleMenu("Measures");
    await toggleMenuItem("Foo");

    checkDatasets(view, ["data", "label"], {
        data: [4, 4],
        label: "Count",
    });

    def.resolve();
    await animationFrame();

    checkDatasets(view, ["data", "label"], {
        data: [82, 4],
        label: "Foo",
    });
});

test("change graph mode while loading a filter", async () => {
    let def;
    onRpc("web_read_group", () => def);
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph type="line">
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="my_filter" string="My Filter" domain="[('id', '&lt;', 2)]" />
            </search>
        `,
    });

    checkDatasets(view, ["data", "label"], {
        data: [4, 4],
        label: "Count",
    });
    checkModeIs(view, "line");

    // Set a domain (this reload is delayed)
    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("My Filter");

    checkDatasets(view, ["data", "label"], {
        data: [4, 4],
        label: "Count",
    });
    checkModeIs(view, "line");

    // Change graph mode
    await selectMode("bar");

    checkDatasets(view, ["data", "label"], {
        data: [4, 4],
        label: "Count",
    });
    checkModeIs(view, "line");

    def.resolve();
    await animationFrame();

    checkDatasets(view, ["data", "label"], {
        data: [1],
        label: "Count",
    });
    checkModeIs(view, "bar");
});

test("only process most recent data for concurrent groupby", async () => {
    let def;
    onRpc(() => def);
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph>
                <field name="product_id" type="row" />
                <field name="foo" type="measure" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="group_by_color" string="Color" context="{ 'group_by': 'color_id' }" />
                <filter name="group_by_date" string="Date" context="{ 'group_by': 'date' }" />
            </search>
        `,
    });

    checkLabels(view, ["xphone", "xpad"]);
    checkDatasets(view, "data", { data: [82, 157] });

    def = new Deferred();
    await toggleSearchBarMenu();
    await toggleMenuItem("Color");
    await toggleMenuItem("Color");
    await toggleMenuItem("Date");
    await toggleMenuItemOption("Date", "Month");

    checkLabels(view, ["xphone", "xpad"]);
    checkDatasets(view, "data", { data: [82, 157] });

    def.resolve();
    await animationFrame();

    checkLabels(view, ["January 2016", "March 2016", "April 2016", "May 2016", "None"]);
    checkDatasets(view, "data", { data: [56, 26, 48, 4, 105] });
});

test("fill_temporal is true by default", async () => {
    expect.assertions(1);

    onRpc("web_read_group", ({ kwargs }) => {
        expect(kwargs.context.fill_temporal).toBe(true, {
            message: "The observable state of fill_temporal should be true",
        });
    });

    await mountView({ type: "graph", resModel: "foo" });
});

test("fill_temporal can be changed throught the context", async () => {
    expect.assertions(1);

    onRpc("web_read_group", ({ kwargs }) => {
        expect(kwargs.context.fill_temporal).toBe(false, {
            message: "The observable state of fill_temporal should be false",
        });
    });

    await mountView({
        type: "graph",
        resModel: "foo",
        context: {
            fill_temporal: false,
        },
    });
});

test("fake data in line chart", async () => {
    mockDate("2020-05-19 01:00:00");

    Foo._records = [];

    await mountView({
        type: "graph",
        resModel: "foo",
        context: {
            search_default_date_filter: 1,
        },
        arch: /* xml */ `
            <graph type="line">
                <field name="date" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="date_filter" domain="[]" date="date" default_period="third_quarter" />
            </search>
        `,
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Date: Previous period");

    expect(".o_graph_canvas_container").toHaveCount(0);
});

test("no filling color for period of comparison", async () => {
    mockDate("2020-05-19 01:00:00");

    for (const record of Foo._records) {
        record.date = record.date?.replace(/^\d{4}/, "2019");
    }

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        context: {
            search_default_date_filter: 1,
        },
        arch: /* xml */ `
            <graph type="line" stacked="0">
                <field name="product_id" />
            </graph>
        `,
        searchViewArch: /* xml */ `
            <search>
                <filter name="date_filter" domain="[]" date="date" default_period="year" />
            </search>
        `,
    });

    await toggleSearchBarMenu();
    await toggleMenuItem("Date: Previous period");

    checkDatasets(view, "backgroundColor", { backgroundColor: "#a7d3f9" });
});

test("group by a non stored, sortable field", async () => {
    // When a field is non-stored but sortable it's inherited
    // from a stored field, so it can be sortable
    Foo._fields.date.store = false;

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        groupBy: ["date:month"],
        arch: /* xml */ `<graph type="line" />`,
    });

    checkLabels(view, ["January 2016", "March 2016", "April 2016", "May 2016"]);
});

test("graph_groupbys should be also used after first load", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        viewId: false,
        groupBy: ["date:quarter"],
        irFilters: [
            {
                user_id: [2, "Mitchell Admin"],
                name: "Favorite",
                id: 1,
                context: JSON.stringify({
                    group_by: [],
                    graph_measure: "revenue",
                    graph_mode: "bar",
                    graph_groupbys: ["color_id"],
                }),
                sort: "[]",
                domain: "",
                is_default: false,
                model_id: "foo",
                action_id: false,
            },
        ],
    });

    checkModeIs(view, "bar");
    checkLabels(view, ["Q1 2016", "Q2 2016", "None"]);
    checkLegend(view, "Count");

    await toggleSearchBarMenu();
    await toggleMenuItem("Favorite");

    checkModeIs(view, "bar");
    checkLabels(view, ["red", "None"]);
    checkLegend(view, "Revenue");
});

test("order='desc' on arch", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph order="desc">
                <field name="date" />
            </graph>
        `,
    });
    checkDatasets(view, ["data", "label"], {
        data: [2, 2, 2, 1, 1],
        label: "Count",
    });
});

test("order='asc' on arch", async () => {
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph order="asc">
                <field name="date" />
            </graph>
        `,
    });
    checkDatasets(view, ["data", "label"], {
        data: [1, 1, 2, 2, 2],
        label: "Count",
    });
});

test("In the middle of a year, a graph view grouped by a date field with granularity 'year' should have a single group of SampleServer.MAIN_RECORDSET_SIZE records", async () => {
    mockDate("2023-06-15 08:00:00");

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph sample="1">
                <field name="date" interval="year" />
            </graph>
        `,
        domain: Domain.FALSE.toList(),
    });

    checkDatasets(view, ["data"], { data: [SampleServer.MAIN_RECORDSET_SIZE] });
});

test("no class 'o_view_sample_data' when real data are presented", async () => {
    Foo._records = [];

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph sample="1">
                <field name="date" />
            </graph>
        `,
    });

    expect(".o_graph_view .o_view_sample_data").toHaveCount(1);
    expect(getChart(view).data.datasets.length).toBeGreaterThan(0);

    await selectMode("line");

    expect(".o_graph_view .o_view_sample_data").toHaveCount(1);
    expect(getChart(view).data.datasets.length).toBeGreaterThan(0);

    await toggleMenu("Measures");
    await toggleMenuItem("Revenue");

    expect(".o_graph_view .o_view_sample_data").toHaveCount(0);
    expect(".o_graph_canvas_container").toHaveCount(0);
});

test("single chart rendering on search", async () => {
    patchWithCleanup(GraphRenderer.prototype, {
        setup() {
            super.setup();

            onRendered(() => expect.step("rendering"));
        },
    });

    await mountView({
        type: "graph",
        resModel: "foo",
    });

    expect.verifySteps(["rendering"]);

    await validateSearch();

    expect.verifySteps(["rendering"]);
});

test("apply default filter label", async () => {
    class CustomGraphModel extends graphView.Model {
        _getDefaultFilterLabel(fields) {
            return "None";
        }
    }
    registry.category("views").add("custom_graph", {
        ...graphView,
        Model: CustomGraphModel,
    });

    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: /* xml */ `
            <graph js_class="custom_graph">
                <field name="product_id" />
                <field name="color_id" />
            </graph>
        `,
    });

    checkLabels(view, ["xphone", "xpad"]);
    checkLegend(view, ["red", "None", "Sum"]);

    await selectMode("line");

    checkLabels(view, ["xphone", "xpad"]);
    checkLegend(view, ["red", "None"]);

    await selectMode("pie");

    checkLabels(view, ["xphone / red", "xphone / None", "xpad / None"]);
    checkLegend(view, ["xphone / red", "xphone / None", "xpad / None"]);
});

test("missing property field definition is fetched", async function () {
    Foo._fields.properties_definition = fields.PropertiesDefinition();
    Foo._fields.parent_id = fields.Many2one({ relation: "foo" });
    Foo._fields.properties = fields.Properties({
        definition_record: "parent_id",
        definition_record_field: "properties_definition",
    });
    onRpc(({ method, kwargs }) => {
        if (method === "web_read_group" && kwargs.groupby?.includes("properties.my_char")) {
            expect.step(JSON.stringify(kwargs.groupby));
            return {
                groups: [
                    {
                        "properties.my_char": false,
                        __domain: [["properties.my_char", "=", false]],
                        __count: 2,
                    },
                    {
                        "properties.my_char": "aaa",
                        __domain: [["properties.my_char", "=", "aaa"]],
                        __count: 1,
                    },
                ],
                length: 2,
            };
        } else if (method === "get_property_definition") {
            return {
                name: "my_char",
                type: "char",
            };
        }
    });
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: `<graph/>`,
        irFilters: [
            {
                user_id: [2, "Mitchell Admin"],
                name: "My Filter",
                id: 5,
                context: `{"group_by": ['properties.my_char']}`,
                sort: "[]",
                domain: "[]",
                is_default: true,
                model_id: "foo",
                action_id: false,
            },
        ],
    });
    expect.verifySteps([`["properties.my_char"]`]);
    checkLabels(view, ["None", "aaa"]);
    checkDatasets(
        view,
        ["data", "label"],
        [
            {
                data: [2, 1],
                label: "Count",
            },
        ]
    );
});

test("missing deleted property field definition is created", async function () {
    Foo._fields.properties_definition = fields.PropertiesDefinition();
    Foo._fields.parent_id = fields.Many2one({ relation: "foo" });
    Foo._fields.properties = fields.Properties({
        definition_record: "parent_id",
        definition_record_field: "properties_definition",
    });
    onRpc(({ method, kwargs }) => {
        if (method === "web_read_group" && kwargs.groupby?.includes("properties.my_char")) {
            expect.step(JSON.stringify(kwargs.groupby));
            return {
                groups: [
                    {
                        "properties.my_char": false,
                        __domain: [["properties.my_char", "=", false]],
                        __count: 2,
                    },
                    {
                        "properties.my_char": "aaa",
                        __domain: [["properties.my_char", "=", "aaa"]],
                        __count: 1,
                    },
                ],
                length: 2,
            };
        } else if (method === "get_property_definition") {
            return {};
        }
    });
    const view = await mountView({
        type: "graph",
        resModel: "foo",
        arch: `<graph/>`,
        irFilters: [
            {
                user_id: [2, "Mitchell Admin"],
                name: "My Filter",
                id: 5,
                context: `{"group_by": ['properties.my_char']}`,
                sort: "[]",
                domain: "[]",
                is_default: true,
                model_id: "foo",
                action_id: false,
            },
        ],
    });
    expect.verifySteps([`["properties.my_char"]`]);
    checkLabels(view, ["None", "aaa"]);
    checkDatasets(
        view,
        ["data", "label"],
        [
            {
                data: [2, 1],
                label: "Count",
            },
        ]
    );
});

test("limit dataset amount", async () => {
    class Project extends models.Model {
        id = fields.Integer();
        name = fields.Char();
    }
    class Stage extends models.Model {
        id = fields.Integer();
        name = fields.Char();
    }
    class Task extends models.Model {
        id = fields.Integer();
        name = fields.Char();
        project_id = fields.Many2one({ relation: "project" });
        stage_id = fields.Many2one({ relation: "stage" });
    }
    defineModels([Project, Stage, Task]);

    for (let i = 1; i <= 600; i++) {
        Project._records.push({
            id: i,
            name: `Project ${i}`,
        });
        Stage._records.push({
            id: i,
            name: `Stage ${i}`,
        });
        Task._records.push({
            id: i,
            project_id: i,
            stage_id: i,
            name: `Task ${i}`,
        });
    }

    const view = await mountView({
        type: "graph",
        resModel: "task",
        arch: `
            <graph>
                <field name="project_id"/>
                <field name="stage_id"/>
            </graph>
        `,
    });
    const model = getGraphModel(view);
    expect(model.data.exceeds).toBe(true);
    expect(model.data.datasets).toHaveLength(80);
    expect(model.data.labels).toHaveLength(80);
    expect(`.o_graph_alert`).toHaveCount(1);

    patchWithCleanup(GraphModel.prototype, {
        notify() {
            expect.step("rerender");
        },
    });
    await contains(`.o_graph_load_all_btn`).click();
    expect.verifySteps(["rerender"]);
    expect(model.data.exceeds).toBe(false);
    expect(model.data.datasets).toHaveLength(600);
    expect(model.data.labels).toHaveLength(600);
});

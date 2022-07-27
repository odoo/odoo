odoo.define('web.graph_view_tests', function (require) {
"use strict";

const searchUtils = require('web.searchUtils');
const GraphView = require('web.GraphView');
const testUtils = require('web.test_utils');
const { sortBy } = require('web.utils');
const { browser } = require('@web/core/browser/browser');
const { legacyExtraNextTick, patchWithCleanup } = require("@web/../tests/helpers/utils");
const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
const legacyViewRegistry = require("web.view_registry");
const { registry } = require("@web/core/registry");

const { createView } = testUtils;
const cpHelpers = require('@web/../tests/search/helpers');
const patchDate = testUtils.mock.patchDate;

const viewRegistry = registry.category("views");

const { INTERVAL_OPTIONS, PERIOD_OPTIONS, COMPARISON_OPTIONS } = searchUtils;
const INTERVAL_OPTION_IDS = Object.keys(INTERVAL_OPTIONS);

const yearIds = [];
const otherIds = [];
for (const id of Object.keys(PERIOD_OPTIONS)) {
    const option = PERIOD_OPTIONS[id];
    if (option.granularity === 'year') {
        yearIds.push(id);
    } else {
        otherIds.push(id);
    }
}
const BASIC_DOMAIN_IDS = [];
for (const yearId of yearIds) {
    BASIC_DOMAIN_IDS.push(yearId);
    for (const id of otherIds) {
        BASIC_DOMAIN_IDS.push(`${yearId}__${id}`);
    }
}
const GENERATOR_INDEXES = {};
Object.keys(PERIOD_OPTIONS).forEach((id, index) => {
    GENERATOR_INDEXES[id] = index;
});

const COMPARISON_OPTION_IDS = Object.keys(COMPARISON_OPTIONS);
const COMPARISON_OPTION_INDEXES = {};
COMPARISON_OPTION_IDS.forEach((id, index) => {
    COMPARISON_OPTION_INDEXES[id] = index;
});

const f = (a, b) => [].concat(...a.map(d => b.map(e => [].concat(d, e))));
const cartesian = (a, b, ...c) => (b ? cartesian(f(a, b), ...c) : a);

const COMBINATIONS = cartesian(COMPARISON_OPTION_IDS, BASIC_DOMAIN_IDS);
const COMBINATIONS_WITH_DATE = cartesian(COMPARISON_OPTION_IDS, BASIC_DOMAIN_IDS, INTERVAL_OPTION_IDS);

function checkDatasets(assert, graph, keys, expectedDatasets) {
    keys = keys instanceof Array ? keys : [keys];
    expectedDatasets = expectedDatasets instanceof Array ?
        expectedDatasets :
        [expectedDatasets];
    const datasets = graph.renderer.componentRef.comp.chart.data.datasets;
    const actualValues = datasets.map(dataset => _.pick(dataset, keys));
    assert.deepEqual(actualValues, expectedDatasets);
}

function checkLabels(assert, graph, expectedLabels) {
    const labels = graph.renderer.componentRef.comp.chart.data.labels;
    assert.deepEqual(labels, expectedLabels);
}

function checkLegend(assert, graph, expectedLegendLabels) {
    expectedLegendLabels = expectedLegendLabels instanceof Array ?
        expectedLegendLabels :
        [expectedLegendLabels];
    const chart = graph.renderer.componentRef.comp.chart;
    const actualLegendLabels = chart.config.options.legend.labels.generateLabels(chart).map(o => o.text);

    assert.deepEqual(actualLegendLabels, expectedLegendLabels);
}

let serverData;
QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: { string: "Foo", type: "integer", store: true },
                    bar: { string: "bar", type: "boolean" },
                    product_id: { string: "Product", type: "many2one", relation: 'product', store: true },
                    color_id: { string: "Color", type: "many2one", relation: 'color' },
                    date: { string: "Date", type: 'date', store: true, sortable: true },
                    revenue: { string: "Revenue", type: 'integer', store: true },
                },
                records: [
                    { id: 1, foo: 3, bar: true, product_id: 37, date: "2016-01-01", revenue: 1 },
                    { id: 2, foo: 53, bar: true, product_id: 37, color_id: 7, date: "2016-01-03", revenue: 2 },
                    { id: 3, foo: 2, bar: true, product_id: 37, date: "2016-03-04", revenue: 3 },
                    { id: 4, foo: 24, bar: false, product_id: 37, date: "2016-03-07", revenue: 4 },
                    { id: 5, foo: 4, bar: false, product_id: 41, date: "2016-05-01", revenue: 5 },
                    { id: 6, foo: 63, bar: false, product_id: 41 },
                    { id: 7, foo: 42, bar: false, product_id: 41 },
                    { id: 8, foo: 48, bar: false, product_id: 41, date: "2016-04-01", revenue: 8 },
                ]
            },
            product: {
                fields: {
                    name: { string: "Product Name", type: "char" }
                },
                records: [{
                    id: 37,
                    display_name: "xphone",
                }, {
                    id: 41,
                    display_name: "xpad",
                }]
            },
            color: {
                fields: {
                    name: { string: "Color", type: "char" }
                },
                records: [{
                    id: 7,
                    display_name: "red",
                }, {
                    id: 14,
                    display_name: "black",
                }]
            },
        };

        serverData = { models: this.data };
    }
}, function () {

    QUnit.module('GraphView (legacy)');

    QUnit.test('simple graph rendering', async function (assert) {
        assert.expect(5);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="bar"/></graph>',
        });

        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
            "should contain a div with a canvas element");
        assert.strictEqual(graph.renderer.props.mode, "bar",
            "should be in bar chart mode by default");

        checkLabels(assert, graph, [[true], [false]]);
        checkDatasets(assert, graph,
            ['backgroundColor', 'data', 'label', 'originIndex', 'stack'],
            {
                backgroundColor: "#1f77b4",
                data: [3, 5],
                label: "Count",
                originIndex: 0,
                stack: "",
            }
        );
        checkLegend(assert, graph, 'Count');

        graph.destroy();
    });

    QUnit.test('default type attribute', async function (assert) {
        assert.expect(1);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" type="pie">
                    <field name="bar"/>
                </graph>`,
        });

        assert.strictEqual(graph.renderer.props.mode, "pie", "should be in pie chart mode by default");

        graph.destroy();
    });

    QUnit.test('title attribute', async function (assert) {
        assert.expect(1);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph title="Partners" type="pie">
                    <field name="bar"/>
                </graph>`,
        });

        assert.strictEqual(graph.$('.o_legacy_graph_renderer label').text(), "Partners",
            "should have 'Partners as title'");

        graph.destroy();
    });

    QUnit.test('field id not in groupBy', async function (assert) {
        assert.expect(1);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="id"/></graph>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.groupby, [],
                        'groupby should not contain id field');
                }
                return this._super.apply(this, arguments);
            },
        });
        graph.destroy();
    });

    QUnit.test('switching mode', async function (assert) {
        assert.expect(6);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph title="Partners" type="line">
                    <field name="bar"/>
                </graph>`,
        });

        assert.strictEqual(graph.renderer.props.mode, "line", "should be in line chart mode by default");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar type button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="line"]'), 'active',
            'line type button should be active');

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="bar"]'));

        assert.strictEqual(graph.renderer.props.mode, "bar", "should be in bar chart mode by default");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="line"]'), 'active',
            'line type button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar type button should be active');

        graph.destroy();
    });

    QUnit.test('displaying line chart with only 1 data point', async function (assert) {
        assert.expect(1);
        // this test makes sure the line chart does not crash when only one data
        // point is displayed.
        this.data.foo.records = this.data.foo.records.slice(0, 1);
        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" type="line">
                    <field name="bar"/>
                </graph>`,
        });

        assert.containsOnce(graph, 'canvas', "should have a canvas");

        graph.destroy();
    });

    QUnit.test('displaying chart data with multiple groupbys', async function (assert) {
        // this test makes sure the line chart shows all data labels (X axis) when
        // it is grouped by several fields
        assert.expect(6);

        const graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: `
                <graph type="bar">
                    <field name="foo"/>
                </graph>`,
            groupBy: ['product_id', 'bar', 'color_id'],
        });

        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, ['true/Undefined', 'true/red', 'false/Undefined']);

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="line"]'));

        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, ['true/Undefined', 'true/red', 'false/Undefined']);

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="pie"]'));

        checkLabels(assert, graph, [
            ["xphone", true, "Undefined"],
            ["xphone", true, "red"],
            ["xphone", false, "Undefined"],
            ["xpad", false, "Undefined"]
        ]);
        checkLegend(assert, graph, [
            'xphone/true/Undefined',
            'xphone/true/red',
            'xphone/false/Undefined',
            'xpad/false/Undefined'
        ]);

        graph.destroy();
    });

    QUnit.test('switching measures', async function (assert) {
        assert.expect(2);

        let rpcCount = 0;

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Gloups">
                    <field name="product_id"/>
                </graph>`,
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        });
        await testUtils.controlPanel.toggleMenu(graph, "Measures");
        await testUtils.controlPanel.toggleMenuItem(graph, "Foo");

        checkLegend(assert, graph, 'Foo');
        assert.strictEqual(rpcCount, 2, "should have done 2 rpcs (2 readgroups)");

        graph.destroy();
    });

    QUnit.test('no content helper (bar chart)', async function (assert) {
        assert.expect(3);
        this.data.foo.records = [];

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Gloups">
                    <field name="product_id"/>
                </graph>`,
            viewOptions: {
                action: {
                    help: '<p class="abc">This helper should not be displayed in graph views</p>'
                }
            },
        });

        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas');
        assert.containsNone(graph, 'div.o_view_nocontent');
        assert.containsNone(graph, '.abc');

        graph.destroy();
    });

    QUnit.test('no content helper (pie chart)', async function (assert) {
        assert.expect(3);
        this.data.foo.records = [];

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph type="pie">
                    <field name="product_id"/>
                </graph>`,
            viewOptions: {
                action: {
                    help: '<p class="abc">This helper should not be displayed in graph views</p>'
                }
            },
        });

        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas');
        assert.containsNone(graph, 'div.o_view_nocontent');
        assert.containsNone(graph, '.abc');

        graph.destroy();
    });

    QUnit.test('render pie chart in comparison mode', async function (assert) {
        assert.expect(2);

        const unpatchDate = patchDate(2020, 4, 19, 1, 0, 0);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            context: { search_default_date_filter: 1, },
            arch: `
                <graph type="pie">
                    <field name="product_id"/>
                </graph>`,
            archs: {
                'foo,false,search': `
                    <search>
                        <filter name="date_filter" domain="[]" date="date" default_period="third_quarter"/>
                    </search>`,
            },
        });

        await cpHelpers.toggleComparisonMenu(graph.el);
        await cpHelpers.toggleMenuItem(graph.el, 'Date: Previous period');

        assert.containsNone(graph, 'div.o_view_nocontent',
            "should not display the no content helper");
        checkLegend(assert, graph, 'No data');

        unpatchDate();
        graph.destroy();
    });

    QUnit.test('fake data in line chart', async function (assert) {
        assert.expect(1);

        const unpatchDate = patchDate(2020, 4, 19, 1, 0, 0);

        this.data.foo.records = [];

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            context: { search_default_date_filter: 1, },
            arch: '<graph type="line">' +
                        '<field name="date"/>' +
                '</graph>',
            archs: {
                'foo,false,search': `
                    <search>
                        <filter name="date_filter" domain="[]" date="date" default_period="third_quarter"/>
                    </search>
                `,
            },
        });

        await cpHelpers.toggleComparisonMenu(graph.el);
        await cpHelpers.toggleMenuItem(graph.el, 'Date: Previous period');

        checkLabels(assert, graph, [[''], ['']]);

        unpatchDate();
        graph.destroy();
    });

    QUnit.test('no filling color for period of comparison', async function (assert) {
        assert.expect(1);

        const unpatchDate = patchDate(2020, 4, 19, 1, 0, 0);

        this.data.foo.records.forEach((r) => {
            if (r.date) {
                r.date = r.date.replace(/\d\d\d\d/, "2019");
            }
        });

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            context: { search_default_date_filter: 1, },
            arch: '<graph type="line">' +
                        '<field name="product_id"/>' +
                '</graph>',
            archs: {
                'foo,false,search': `
                    <search>
                        <filter name="date_filter" domain="[]" date="date" default_period="this_year"/>
                    </search>
                `,
            },
        });

        await cpHelpers.toggleComparisonMenu(graph.el);
        await cpHelpers.toggleMenuItem(graph.el, 'Date: Previous period');

        checkDatasets(assert, graph, ["data", "backgroundColor"], { data: [4, 2] });

        unpatchDate();
        graph.destroy();
    });

    QUnit.test('no content helper after update', async function (assert) {
        assert.expect(6);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Gloups">
                    <field name="product_id"/>
                </graph>`,
            viewOptions: {
                action: {
                    help: '<p class="abc">This helper should not be displayed in graph views</p>'
                }
            },
        });

        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas');
        assert.containsNone(graph, 'div.o_view_nocontent');
        assert.containsNone(graph, '.abc');

        await testUtils.graph.reload(graph, { domain: [['product_id', '=', 4]] });
        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas');
        assert.containsNone(graph, 'div.o_view_nocontent');
        assert.containsNone(graph, '.abc');
        graph.destroy();
    });

    QUnit.test('can reload with other group by', async function (assert) {
        assert.expect(2);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Gloups">
                    <field name="product_id"/>
                </graph>`,
        });

        checkLabels(assert, graph, [['xphone'], ['xpad']]);

        await testUtils.graph.reload(graph, { groupBy: ['color_id'] });
        checkLabels(assert, graph, [['Undefined'], ['red']]);

        graph.destroy();
    });

    QUnit.test('getOwnedQueryParams correctly returns mode, measure, and groupbys', async function (assert) {
        assert.expect(4);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Gloups">
                    <field name="product_id"/>
                </graph>`,
        });

        assert.deepEqual(graph.getOwnedQueryParams(), {
            context: {
                graph_mode: 'bar',
                graph_measure: '__count__',
                graph_groupbys: ['product_id'],
            }
        }, "context should be correct");

        await testUtils.controlPanel.toggleMenu(graph, "Measures");
        await testUtils.controlPanel.toggleMenuItem(graph, "Foo");

        assert.deepEqual(graph.getOwnedQueryParams(), {
            context: {
                graph_mode: 'bar',
                graph_measure: 'foo',
                graph_groupbys: ['product_id'],
            },
        }, "context should be correct");

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="line"]'));
        assert.deepEqual(graph.getOwnedQueryParams(), {
            context: {
                graph_mode: 'line',
                graph_measure: 'foo',
                graph_groupbys: ['product_id'],
            },
        }, "context should be correct");

        await testUtils.graph.reload(graph, { groupBy: ['product_id', 'color_id'] }); // change groupbys
        assert.deepEqual(graph.getOwnedQueryParams(), {
            context: {
                graph_mode: 'line',
                graph_measure: 'foo',
                graph_groupbys: ['product_id', 'color_id'],
            },
        }, "context should be correct");

        graph.destroy();
    });

    QUnit.test('correctly uses graph_ keys from the context', async function (assert) {
        assert.expect(5);

        const lastOne = this.data.foo.records[this.data.foo.records.length - 1];
        lastOne.color_id = 14;

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
            viewOptions: {
                context: {
                    graph_measure: 'foo',
                    graph_mode: 'line',
                    graph_groupbys: ['color_id'],
                },
            },
        });
        // check measure name is present in legend
        checkLegend(assert, graph, 'Foo');
        // check mode
        assert.strictEqual(graph.renderer.props.mode, "line", "should be in line chart mode");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar chart button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="line"]'), 'active',
            'line chart button should be active');
        // check groupby values ('Undefined' is rejected in line chart) are in labels
        checkLabels(assert, graph, [['red'], ['black']]);

        graph.destroy();
    });

    QUnit.test('correctly use group_by key from the context', async function (assert) {
        assert.expect(1);

        const lastOne = this.data.foo.records[this.data.foo.records.length - 1];
        lastOne.color_id = 14;

        const graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
            groupBy: ['color_id'],
            viewOptions: {
                context: {
                    graph_measure: 'foo',
                    graph_mode: 'line',
                },
            },
        });
        // check groupby values ('Undefined' is rejected in line chart) are in labels
        checkLabels(assert, graph, [['red'], ['black']]);

        graph.destroy();
    });

    QUnit.test('correctly uses graph_ keys from the context (at reload)', async function (assert) {
        assert.expect(7);

        const lastOne = this.data.foo.records[this.data.foo.records.length - 1];
        lastOne.color_id = 14;

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
        });

        assert.strictEqual(graph.renderer.props.mode, "bar", "should be in bar chart mode");
        assert.hasClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar chart button should be active');

        const reloadParams = {
            context: {
                graph_measure: 'foo',
                graph_mode: 'line',
                graph_groupbys: ['color_id'],
            },
        };
        await testUtils.graph.reload(graph, reloadParams);

        // check measure
        checkLegend(assert, graph, 'Foo');
        // check mode
        assert.strictEqual(graph.renderer.props.mode, "line", "should be in line chart mode");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar chart button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="line"]'), 'active',
            'line chart button should be active');
        // check groupby values ('Undefined' is rejected in line chart) are in labels
        checkLabels(assert, graph, [['red'], ['black']]);

        graph.destroy();
    });

    QUnit.test('reload graph with correct fields', async function (assert) {
        assert.expect(2);

        const graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: `
                <graph>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </graph>`,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['product_id', 'foo'],
                        "should read the correct fields");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.graph.reload(graph, { groupBy: [] });

        graph.destroy();
    });

    QUnit.test('initial groupby is kept when reloading', async function (assert) {
        assert.expect(8);

        const graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: `
                <graph>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </graph>`,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.groupby, ['product_id'],
                        "should group by the correct field");
                }
                return this._super.apply(this, arguments);
            },
        });

        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, 'Foo');
        checkDatasets(assert, graph, 'data', { data: [82, 157] });

        await testUtils.graph.reload(graph, { groupBy: [] });
        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, 'Foo');
        checkDatasets(assert, graph, 'data', { data: [82, 157] });

        graph.destroy();
    });

    QUnit.test('only process most recent data for concurrent groupby', async function (assert) {
        assert.expect(4);

        const graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: `
                <graph>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="measure"/>
                </graph>`,
        });

        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkDatasets(assert, graph, 'data', {data: [82, 157]});

        testUtils.graph.reload(graph, {groupBy: ['color_id']});
        await testUtils.graph.reload(graph, {groupBy: ['date:month']});
        checkLabels(assert, graph, [['January 2016'], ['March 2016'], ['May 2016'], ['Undefined'], ['April 2016']]);
        checkDatasets(assert, graph, 'data', {data: [56, 26, 4, 105, 48]});

        graph.destroy();
    });

    QUnit.test('use a many2one as a measure should work (without groupBy)', async function (assert) {
        assert.expect(4);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners">
                    <field name="product_id" type="measure"/>
                </graph>`,
        });
        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
            "should contain a div with a canvas element");
        checkLabels(assert, graph, [[]]);
        checkLegend(assert, graph, 'Product');
        checkDatasets(assert, graph, 'data', { data: [2] });

        graph.destroy();
    });

    QUnit.test('use a many2one as a measure should work (with groupBy)', async function (assert) {
        assert.expect(5);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners">
                    <field name="bar" type="row"/>
                    <field name="product_id" type="measure"/>
                </graph>`,
        });
        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
            "should contain a div with a canvas element");

        assert.strictEqual(graph.renderer.props.mode, "bar",
            "should be in bar chart mode by default");
        checkLabels(assert, graph, [[true], [false]]);
        checkLegend(assert, graph, 'Product');
        checkDatasets(assert, graph, 'data', { data: [1, 2] });

        graph.destroy();
    });

    QUnit.test('use a many2one as a measure and as a groupby should work', async function (assert) {
        assert.expect(3);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners">
                    <field name="product_id" type="row"/>
                </graph>`,
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });

        // need to set the measure this way because it cannot be set in the
        // arch.
        await testUtils.controlPanel.toggleMenu(graph, "Measures");
        await testUtils.controlPanel.toggleMenuItem(graph, "Product");

        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, 'Product');
        checkDatasets(assert, graph, 'data', { data: [1, 1] });

        graph.destroy();
    });

    QUnit.test('not use a many2one as a measure by default', async function (assert) {
        assert.expect(1);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
        });
        assert.notOk(graph.measures.product_id,
            "should not have product_id as measure");
        graph.destroy();
    });

    QUnit.test('use a many2one as a measure if set as additional fields', async function (assert) {
        assert.expect(1);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });

        assert.ok(graph.measures.find(m => m.fieldName === 'product_id'),
            "should have product_id as measure");

        graph.destroy();
    });

    QUnit.test('measure dropdown consistency', async function (assert) {
        assert.expect(2);

        serverData.views = {
            'foo,false,graph': `
                <graph string="Partners" type="bar">
                    <field name="foo" type="measure"/>
                </graph>`,
            'foo,false,search': `<search/>`,
            'foo,false,kanban': `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
        };

        viewRegistry.remove("graph");
        legacyViewRegistry.add("graph", GraphView); // We want to test the legacy view that was not added to viewRegistry!
        // (see end of registerView in legacy_views.js)

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            res_model: 'foo',
            type: 'ir.actions.act_window',
            views: [[false, 'graph'], [false, 'kanban']],
            flags: {
                graph: {
                    additionalMeasures: ['product_id'],
                }
            },
        });

        assert.containsOnce(webClient, '.o_control_panel .o_graph_measures_list',
            "Measures dropdown is present at init"
        );

        await cpHelpers.switchView(webClient, 'kanban');
        await legacyExtraNextTick();
        await cpHelpers.switchView(webClient, 'graph');
        await legacyExtraNextTick();

        assert.containsOnce(webClient, '.o_control_panel .o_graph_measures_list',
            "Measures dropdown is present after reload"
        );
    });

    QUnit.test('graph view crash when moving from search view using Down key', async function (assert) {
        assert.expect(1);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" type="pie">
                    <field name="bar"/>
                </graph>`,
        });
        graph._giveFocus();
        assert.ok(true, "should not generate any error");
        graph.destroy();
    });

    QUnit.test('graph measures should be alphabetically sorted', async function (assert) {
        assert.expect(2);

        const data = this.data;
        data.foo.fields.bouh = { string: "bouh", type: "integer" };

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: data,
            arch: `
                <graph string="Partners">
                    <field name="foo" type="measure"/>
                    <field name="bouh" type="measure"/>
                </graph>`,
        });

        await testUtils.controlPanel.toggleMenu(graph, "Measures");
        assert.strictEqual(graph.$buttons.find('.o_graph_measures_list .dropdown-item:first').text(), 'bouh',
            "Bouh should be the first measure");
        assert.strictEqual(graph.$buttons.find('.o_graph_measures_list .dropdown-item:last').text(), 'Count',
            "Count should be the last measure");

        graph.destroy();
    });

    QUnit.test('graph view with string attribute on view architecture fields', async function (assert) {
        assert.expect(4);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
            <graph string="Partners">
                <field name="product_id" type="measure" string="Jethalal"/>
                <field name="foo" type="measure"/>
            </graph>`,
        });

        checkLegend(assert, graph, 'Foo');
        let chart = graph.renderer.componentRef.comp.chart;
        let yAxisLabel = chart.config.options.scales.yAxes[0].scaleLabel.labelString;
        assert.strictEqual(yAxisLabel, "Foo");

        await testUtils.controlPanel.toggleMenu(graph, "Measures");
        await testUtils.controlPanel.toggleMenuItem(graph, "Jethalal");
        checkLegend(assert, graph, 'Jethalal');

        chart = graph.renderer.componentRef.comp.chart;
        yAxisLabel = chart.config.options.scales.yAxes[0].scaleLabel.labelString;
        assert.strictEqual(yAxisLabel, "Jethalal");

        graph.destroy();
    });

    QUnit.test('graph view "graph_measure" field in context not in measures', async function (assert) {
        assert.expect(2);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
            viewOptions: {
                context: {
                    graph_measure: 'product_id',
                },
            },
        });

        checkLegend(assert, graph, 'Product');
        let chart = graph.renderer.componentRef.comp.chart;
        let yAxisLabel = chart.config.options.scales.yAxes[0].scaleLabel.labelString;
        assert.strictEqual(yAxisLabel, "Product");

        graph.destroy();
    });

    QUnit.test('Undefined should appear in bar, pie graph but not in line graph', async function (assert) {
        assert.expect(3);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            groupBy: ['date'],
            data: this.data,
            arch: `
                <graph string="Partners" type="line">
                    <field name="bar"/>
                </graph>`,
        });

        function indexOf(label) {
            return graph.renderer.componentRef.comp.chart.data.labels.findIndex(
                (lab) => JSON.stringify(lab) === JSON.stringify(label)
            );
        }

        assert.strictEqual(indexOf(['Undefined']), -1);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=bar]'));
        assert.ok(indexOf(['Undefined']) >= 0);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=pie]'));
        assert.ok(indexOf(['Undefined']) >= 0);

        graph.destroy();
    });

    QUnit.test('Undefined should appear in bar, pie graph but not in line graph with multiple groupbys', async function (assert) {
        assert.expect(4);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            groupBy: ['date', 'color_id'],
            data: this.data,
            arch: `
                <graph string="Partners" type="line">
                    <field name="bar"/>
                </graph>`,
        });

        function indexOf(label) {
            return graph.renderer.componentRef.comp.chart.data.labels.findIndex(
                (lab) => JSON.stringify(lab) === JSON.stringify(label)
            );
        }

        assert.strictEqual(indexOf(['Undefined']), -1);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=bar]'));
        assert.ok(indexOf(['Undefined']) >= 0);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=pie]'));
        const labels = graph.renderer.componentRef.comp.chart.data.labels;
        assert.ok(labels.filter(label => /Undefined/.test(label.join(''))).length >= 1);

        // Undefined should not appear after switching back to line chart
        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=line]'));
        assert.strictEqual(indexOf(['Undefined']), -1);

        graph.destroy();
    });

    QUnit.test('no comparison and no groupby', async function (assert) {
        assert.expect(9);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" type="bar">
                    <field name="foo" type="measure"/>
                </graph>`,
        });


        checkLabels(assert, graph, [[]]);
        checkLegend(assert, graph, 'Foo');
        checkDatasets(assert, graph, 'data', { data: [239] });

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=line]'));
        // the labels in line chart is translated in this case to avoid to have a single
        // point at the left of the screen and chart to seem empty.
        checkLabels(assert, graph, [[''], [], ['']]);
        checkLegend(assert, graph, 'Foo');
        checkDatasets(assert, graph, 'data', { data: [undefined, 239] });
        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=pie]'));
        checkLabels(assert, graph, [[]]);
        checkLegend(assert, graph, 'Total');
        checkDatasets(assert, graph, 'data', { data: [239] });

        graph.destroy();
    });

    QUnit.test('no comparison and one groupby', async function (assert) {
        assert.expect(9);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" type="bar">
                    <field name="foo" type="measure"/>
                    <field name="bar" type="row"/>
                </graph>`,
        });

        checkLabels(assert, graph, [[true], [false]]);
        checkLegend(assert, graph, 'Foo');
        checkDatasets(assert, graph, 'data', { data: [58, 181] });

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=line]'));
        checkLabels(assert, graph, [[true], [false]]);
        checkLegend(assert, graph, 'Foo');
        checkDatasets(assert, graph, 'data', { data: [58, 181] });

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=pie]'));

        checkLabels(assert, graph, [[true], [false]]);
        checkLegend(assert, graph, ['true', 'false']);
        checkDatasets(assert, graph, 'data', { data: [58, 181] });

        graph.destroy();
    });
    QUnit.test('no comparison and two groupby', async function (assert) {
        assert.expect(9);
        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" type="bar">
                    <field name="foo" type="measure"/>
                </graph>`,
            groupBy: ['product_id', 'color_id'],
        });

        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, ['Undefined', 'red']);
        checkDatasets(assert, graph, ['label', 'data'], [
            {
                label: 'Undefined',
                data: [29, 157],
            },
            {
                label: 'red',
                data: [53, 0],
            }
        ]);

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=line]'));
        checkLabels(assert, graph, [['xphone'], ['xpad']]);
        checkLegend(assert, graph, ['Undefined', 'red']);
        checkDatasets(assert, graph, ['label', 'data'], [
            {
                label: 'Undefined',
                data: [29, 157],
            },
            {
                label: 'red',
                data: [53, 0],
            }
        ]);

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=pie]'));
        checkLabels(assert, graph, [['xphone', 'Undefined'], ['xphone', 'red'], ['xpad', 'Undefined']]);
        checkLegend(assert, graph, ['xphone/Undefined', 'xphone/red', 'xpad/Undefined']);
        checkDatasets(assert, graph, ['label', 'data'], {
            label: '',
            data: [29, 53, 157],
        });

        graph.destroy();
    });

    QUnit.test('graph view only keeps finer groupby filter option for a given groupby', async function (assert) {
        assert.expect(3);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            groupBy: ['date:year', 'product_id', 'date', 'date:quarter'],
            data: this.data,
            arch: `
                <graph string="Partners" type="line">
                    <field name="bar"/>
                </graph>`,
        });

        checkLabels(assert, graph, [["January 2016"], ["March 2016"], ["May 2016"], ["April 2016"]]);
        // mockReadGroup does not always sort groups -> May 2016 is before April 2016 for that reason.
        checkLegend(assert, graph, ["xphone", "xpad"]);
        checkDatasets(assert, graph, ['label', 'data'], [
            {
                label: 'xphone',
                data: [2, 2, 0, 0],
            }, {
                label: 'xpad',
                data: [0, 0, 1, 1],
            }
        ]);

        graph.destroy();
    });

    QUnit.test('clicking on bar and pie charts triggers a do_action', async function (assert) {
        assert.expect(5);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Foo Analysis">
                    <field name="bar"/>
                </graph>`,
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action, {
                        context: {},
                        domain: [["bar", "=", true]],
                        name: "Foo Analysis",
                        res_model: "foo",
                        target: 'current',
                        type: 'ir.actions.act_window',
                        view_mode: 'list',
                        views: [[false, 'list'], [false, 'form']],
                    }, "should trigger do_action with correct action parameter");
                }
            },
        });

        // bar mode
        assert.strictEqual(graph.renderer.props.mode, "bar", "should be in bar chart mode");
        checkDatasets(assert, graph, ['domain'], {
            domain: [[["bar", "=", true]], [["bar", "=", false]]],
        });

        let myChart = graph.renderer.componentRef.comp.chart;
        let meta = myChart.getDatasetMeta(0);
        let rectangle = myChart.canvas.getBoundingClientRect();
        let point = meta.data[0].getCenterPoint();
        await testUtils.dom.triggerEvent(myChart.canvas, 'click', {
            pageX: rectangle.left + point.x,
            pageY: rectangle.top + point.y
        });

        // pie mode
        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=pie]'));
        assert.strictEqual(graph.renderer.props.mode, "pie", "should be in pie chart mode");

        myChart = graph.renderer.componentRef.comp.chart;
        meta = myChart.getDatasetMeta(0);
        rectangle = myChart.canvas.getBoundingClientRect();
        point = meta.data[0].getCenterPoint();
        await testUtils.dom.triggerEvent(myChart.canvas, 'click', {
            pageX: rectangle.left + point.x,
            pageY: rectangle.top + point.y
        });

        graph.destroy();
    });

    QUnit.test('clicking charts trigger a do_action with correct views', async function (assert) {
        assert.expect(3);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Foo Analysis">
                    <field name="bar"/>
                </graph>`,
            intercepts: {
                do_action: function (ev) {
                    assert.deepEqual(ev.data.action, {
                        context: {},
                        domain: [["bar", "=", true]],
                        name: "Foo Analysis",
                        res_model: "foo",
                        target: 'current',
                        type: 'ir.actions.act_window',
                        view_mode: 'list',
                        views: [[364, 'list'], [29, 'form']],
                    }, "should trigger do_action with correct action parameter");
                }
            },
            viewOptions: {
                actionViews: [{
                    type: 'list',
                    viewID: 364,
                }, {
                    type: 'form',
                    viewID: 29,
                }],
            },
        });

        assert.strictEqual(graph.renderer.props.mode, "bar", "should be in bar chart mode");
        checkDatasets(assert, graph, ['domain'], {
            domain: [[["bar", "=", true]], [["bar", "=", false]]],
        });

        let myChart = graph.renderer.componentRef.comp.chart;
        let meta = myChart.getDatasetMeta(0);
        let rectangle = myChart.canvas.getBoundingClientRect();
        let point = meta.data[0].getCenterPoint();
        await testUtils.dom.triggerEvent(myChart.canvas, 'click', {
            pageX: rectangle.left + point.x,
            pageY: rectangle.top + point.y
        });

        graph.destroy();
    });

    QUnit.test('graph view with attribute disable_linking="True"', async function (assert) {
        assert.expect(2);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph disable_linking="1">
                    <field name="bar"/>
                </graph>`,
            intercepts: {
                do_action: function () {
                    throw new Error('Should not perform a do_action');
                },
            },
        });

        assert.strictEqual(graph.renderer.props.mode, "bar", "should be in bar chart mode");
        checkDatasets(assert, graph, ['domain'], {
            domain: [[["bar", "=", true]], [["bar", "=", false]]],
        });

        let myChart = graph.renderer.componentRef.comp.chart;
        let meta = myChart.getDatasetMeta(0);
        let rectangle = myChart.canvas.getBoundingClientRect();
        let point = meta.data[0].getCenterPoint();
        await testUtils.dom.triggerEvent(myChart.canvas, 'click', {
            pageX: rectangle.left + point.x,
            pageY: rectangle.top + point.y
        });

        graph.destroy();
    });

    QUnit.test('graph view without invisible attribute on field', async function (assert) {
        assert.expect(4);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `<graph string="Partners"/>`,
        });

        await testUtils.dom.click(graph.$('.btn-group:first button'));
        assert.containsN(graph, 'li.o_menu_item', 3,
            "there should be three menu item in the measures dropdown (count, revenue and foo)");
        assert.containsOnce(graph, 'li.o_menu_item a:contains("Revenue")');
        assert.containsOnce(graph, 'li.o_menu_item a:contains("Foo")');
        assert.containsOnce(graph, 'li.o_menu_item a:contains("Count")');

        graph.destroy();
    });

    QUnit.test('graph view with invisible attribute on field', async function (assert) {
        assert.expect(2);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners">
                    <field name="revenue" invisible="1"/>
                </graph>`,
        });

        await testUtils.dom.click(graph.$('.btn-group:first button'));
        assert.containsN(graph, 'li.o_menu_item', 2,
            "there should be only two menu item in the measures dropdown (count and foo)");
        assert.containsNone(graph, 'li.o_menu_item a:contains("Revenue")');

        graph.destroy();
    });

    QUnit.test('graph view sort by measure', async function (assert) {
        assert.expect(18);

        // change first record from foo as there are 4 records count for each product
        this.data.product.records.push({ id: 38, display_name: "zphone" });
        this.data.foo.records[7].product_id = 38;

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners" order="desc">
                    <field name="product_id"/>
                </graph>`,
        });

        assert.containsN(graph, 'button[data-order]', 2,
            "there should be two order buttons for sorting axis labels in bar mode");
        checkLegend(assert, graph, 'Count', 'measure should be by count');
        assert.hasClass(graph.$('button[data-order="desc"]'), 'active',
            'sorting should be applie on descending order by default when sorting="desc"');
        checkDatasets(assert, graph, 'data', { data: [4, 3, 1] });

        await testUtils.dom.click(graph.$buttons.find('button[data-order="asc"]'));
        assert.hasClass(graph.$('button[data-order="asc"]'), 'active',
            "ascending order should be applied");
        checkDatasets(assert, graph, 'data', { data: [1, 3, 4] });

        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.hasClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order button should be active");
        checkDatasets(assert, graph, 'data', { data: [4, 3, 1] });

        // again click on descending button to deactivate order button
        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.doesNotHaveClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order button should not be active");
        checkDatasets(assert, graph, 'data', { data: [4, 3, 1] });

        // set line mode
        await testUtils.dom.click(graph.$buttons.find('button[data-mode="line"]'));
        assert.containsN(graph, 'button[data-order]', 2,
            "there should be two order buttons for sorting axis labels in line mode");
        checkLegend(assert, graph, 'Count', 'measure should be by count');
        assert.doesNotHaveClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order should be applied");
        checkDatasets(assert, graph, 'data', { data: [4, 3, 1] });

        await testUtils.dom.click(graph.$buttons.find('button[data-order="asc"]'));
        assert.hasClass(graph.$('button[data-order="asc"]'), 'active',
            "ascending order button should be active");
        checkDatasets(assert, graph, 'data', { data: [1, 3, 4] });

        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.hasClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order button should be active");
        checkDatasets(assert, graph, 'data', { data: [4, 3, 1] });

        graph.destroy();
    });

    QUnit.test('graph view sort by measure for grouped data', async function (assert) {
        assert.expect(9);

        // change first record from foo as there are 4 records count for each product
        this.data.product.records.push({ id: 38, display_name: "zphone", });
        this.data.foo.records[7].product_id = 38;

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners">
                    <field name="product_id"/>
                    <field name="bar"/>
                </graph>`,
        });

        checkLegend(assert, graph, ["true", "false"], 'measure should be by count');
        assert.containsN(graph, 'button[data-order]', 2,
            "there should be two order buttons for sorting axis labels");
        checkDatasets(assert, graph, 'data', [{ data: [3, 0, 0] }, { data: [1, 3, 1] }]);

        await testUtils.dom.click(graph.$buttons.find('button[data-order="asc"]'));
        assert.hasClass(graph.$('button[data-order="asc"]'), 'active',
            "ascending order should be applied by default");
        checkDatasets(assert, graph, 'data', [{ data: [1, 3, 1] }, { data: [0, 0, 3] }]);

        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.hasClass(graph.$('button[data-order="desc"]'), 'active',
            "ascending order button should be active");
        checkDatasets(assert, graph, 'data', [{ data: [3, 0, 0] }, { data: [1, 3, 1] }]);

        // again click on descending button to deactivate order button
        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.doesNotHaveClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order button should not be active");
        checkDatasets(assert, graph, 'data', [{ data: [3, 0, 0] }, { data: [1, 3, 1] }]);

        graph.destroy();
    });

    QUnit.test('graph view sort by measure for multiple grouped data', async function (assert) {
        assert.expect(9);

        // change first record from foo as there are 4 records count for each product
        this.data.product.records.push({ id: 38, display_name: "zphone" });
        this.data.foo.records[7].product_id = 38;

        // add few more records to data to have grouped data date wise
        const data = [
            { id: 9, foo: 48, bar: false, product_id: 41, date: "2016-04-01" },
            { id: 10, foo: 49, bar: false, product_id: 41, date: "2016-04-01" },
            { id: 11, foo: 50, bar: true, product_id: 37, date: "2016-01-03" },
            { id: 12, foo: 50, bar: true, product_id: 41, date: "2016-01-03" },
        ];

        Object.assign(this.data.foo.records, data);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph string="Partners">
                    <field name="product_id"/>
                    <field name="date"/>
                </graph>`,
            groupBy: ['date', 'product_id']
        });

        checkLegend(assert, graph, ["xpad", "xphone", "zphone"], 'measure should be by count');
        assert.containsN(graph, 'button[data-order]', 2,
            "there should be two order buttons for sorting axis labels");
        checkDatasets(assert, graph, 'data', [{ data: [2, 1, 1, 2] }, { data: [0, 1, 0, 0] }, { data: [1, 0, 0, 0] }]);

        await testUtils.dom.click(graph.$buttons.find('button[data-order="asc"]'));
        assert.hasClass(graph.$('button[data-order="asc"]'), 'active',
            "ascending order should be applied by default");
        checkDatasets(assert, graph, 'data', [{ data: [1, 1, 2, 2] }, { data: [0, 1, 0, 0] }, { data: [0, 0, 0, 1] }]);

        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.hasClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order button should be active");
        checkDatasets(assert, graph, 'data', [{ data: [2, 1, 2, 1] }, { data: [1, 0, 0, 0] }, { data: [0, 1, 0, 0] }]);

        // again click on descending button to deactivate order button
        await testUtils.dom.click(graph.$buttons.find('button[data-order="desc"]'));
        assert.doesNotHaveClass(graph.$('button[data-order="desc"]'), 'active',
            "descending order button should not be active");
        checkDatasets(assert, graph, 'data', [{ data: [2, 1, 1, 2] }, { data: [0, 1, 0, 0] }, { data: [1, 0, 0, 0] }]);

        graph.destroy();
    });

    QUnit.test('empty graph view with sample data', async function (assert) {
        assert.expect(8);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph sample="1">
                    <field name="product_id"/>
                    <field name="date"/>
                </graph>`,
            domain: [['id', '<', 0]],
            viewOptions: {
                action: {
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        });

        assert.hasClass(graph.el, 'o_view_sample_data');
        assert.containsOnce(graph, '.o_view_nocontent');
        assert.containsOnce(graph, '.o_graph_canvas_container canvas');
        assert.hasClass(graph.$('.o_graph_canvas_container'), 'o_sample_data_disabled');

        await graph.reload({ domain: [] });

        assert.doesNotHaveClass(graph.el, 'o_view_sample_data');
        assert.containsNone(graph, '.o_view_nocontent');
        assert.containsOnce(graph, '.o_graph_canvas_container canvas');
        assert.doesNotHaveClass(graph.$('.o_graph_canvas_container'), 'o_sample_data_disabled');

        graph.destroy();
    });

    QUnit.test('non empty graph view with sample data', async function (assert) {
        assert.expect(8);

        const graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: `
                <graph sample="1">
                    <field name="product_id"/>
                    <field name="date"/>
                </graph>`,
            viewOptions: {
                action: {
                    help: '<p class="abc">click to add a foo</p>'
                }
            },
        })

        assert.doesNotHaveClass(graph.el, 'o_view_sample_data');
        assert.containsNone(graph, '.o_view_nocontent');
        assert.containsOnce(graph, '.o_graph_canvas_container canvas');
        assert.doesNotHaveClass(graph.$('.o_graph_canvas_container'), 'o_sample_data_disabled');

        await graph.reload({ domain: [['id', '<', 0]] });

        assert.doesNotHaveClass(graph.el, 'o_view_sample_data');
        assert.containsOnce(graph, '.o_graph_canvas_container canvas');
        assert.doesNotHaveClass(graph.$('.o_graph_canvas_container'), 'o_sample_data_disabled');
        assert.containsNone(graph, '.o_view_nocontent');

        graph.destroy();
    });

    QUnit.module('GraphView: comparison mode (legacy)', {
        beforeEach: async function () {
            this.data.foo.records[0].date = '2016-12-15';
            this.data.foo.records[1].date = '2016-12-17';
            this.data.foo.records[2].date = '2016-11-22';
            this.data.foo.records[3].date = '2016-11-03';
            this.data.foo.records[4].date = '2016-12-20';
            this.data.foo.records[5].date = '2016-12-19';
            this.data.foo.records[6].date = '2016-12-15';
            this.data.foo.records[7].date = undefined;

            this.data.foo.records.push({ id: 9, foo: 48, bar: false, product_id: 41, color_id: 7, date: "2016-12-01" });
            this.data.foo.records.push({ id: 10, foo: 17, bar: true, product_id: 41, color_id: 7, date: "2016-12-01" });
            this.data.foo.records.push({ id: 11, foo: 45, bar: true, product_id: 37, color_id: 14, date: "2016-12-01" });
            this.data.foo.records.push({ id: 12, foo: 48, bar: false, product_id: 37, color_id: 7, date: "2016-12-10" });
            this.data.foo.records.push({ id: 13, foo: 48, bar: false, product_id: undefined, color_id: 14, date: "2016-11-30" });
            this.data.foo.records.push({ id: 14, foo: -50, bar: true, product_id: 41, color_id: 14, date: "2016-12-15" });
            this.data.foo.records.push({ id: 15, foo: 53, bar: false, product_id: 41, color_id: 14, date: "2016-11-01" });
            this.data.foo.records.push({ id: 16, foo: 53, bar: true, product_id: undefined, color_id: 7, date: "2016-09-01" });
            this.data.foo.records.push({ id: 17, foo: 48, bar: false, product_id: 41, color_id: undefined, date: "2016-08-01" });
            this.data.foo.records.push({ id: 18, foo: -156, bar: false, product_id: 37, color_id: undefined, date: "2016-07-15" });
            this.data.foo.records.push({ id: 19, foo: 31, bar: false, product_id: 41, color_id: 14, date: "2016-12-15" });
            this.data.foo.records.push({ id: 20, foo: 109, bar: true, product_id: 41, color_id: 7, date: "2015-06-01" });

            this.data.foo.records = sortBy(this.data.foo.records, 'date');

            this.unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

            patchWithCleanup(browser, { setTimeout: (fn) => fn() });

            const graph = await createView({
                View: GraphView,
                model: "foo",
                data: this.data,
                arch: `
                    <graph string="Partners" type="bar">
                        <field name="foo" type="measure"/>
                    </graph>`,
                archs: {
                    'foo,false,search': `
                        <search>
                            <filter name="date" string="Date" context="{'group_by': 'date'}"/>
                            <filter name="date_filter" string="Date Filter" date="date"/>
                            <filter name="bar" string="Bar" context="{'group_by': 'bar'}"/>
                            <filter name="product_id" string="Product" context="{'group_by': 'product_id'}"/>
                            <filter name="color_id" string="Color" context="{'group_by': 'color_id'}"/>
                        </search>`,
                },
                viewOptions: {
                    additionalMeasures: ['product_id'],
                },
            });

            this.graph = graph;

            const checkOnlyToCheck = true;
            const exhaustiveTest = false || checkOnlyToCheck;

            const self = this;
            async function* graphGenerator(combinations) {
                let i = 0;
                while (i < combinations.length) {
                    const combination = combinations[i];
                    if (!checkOnlyToCheck || combination.toString() in self.combinationsToCheck) {
                        await self.setConfig(combination);
                    }
                    if (exhaustiveTest) {
                        i++;
                    } else {
                        i += Math.floor(1 + Math.random() * 20);
                    }
                    yield combination;
                }
            }

            this.combinationsToCheck = {};
            this.testCombinations = async (combinations, assert) => {
                for await (const combination of graphGenerator(combinations)) {
                    // we can check particular combinations here
                    if (combination.toString() in this.combinationsToCheck) {
                        if (this.combinationsToCheck[combination].errorMessage) {
                            assert.strictEqual(
                                graph.$('.o_nocontent_help p').eq(1).text().trim(),
                                this.combinationsToCheck[combination].errorMessage
                            );
                        } else {
                            checkLabels(assert, graph, this.combinationsToCheck[combination].labels);
                            checkLegend(assert, graph, this.combinationsToCheck[combination].legend);
                            checkDatasets(assert, graph, ['label', 'data'], this.combinationsToCheck[combination].datasets);
                        }
                    }
                }
            };

            this.selectTimeRanges = async (comparisonOptionId, basicDomainId) => {
                const facetEls = graph.el.querySelectorAll('.o_searchview_facet');
                const facetIndex = [...facetEls].findIndex(el => !!el.querySelector('span.fa-filter'));
                if (facetIndex > -1) {
                    await cpHelpers.removeFacet(graph.el, facetIndex);
                }
                const [yearId, otherId] = basicDomainId.split('__');
                await cpHelpers.toggleFilterMenu(graph.el);
                await cpHelpers.toggleMenuItem(graph.el, 'Date Filter');
                await cpHelpers.toggleMenuItemOption(graph.el, 'Date Filter', GENERATOR_INDEXES[yearId]);
                if (otherId) {
                    await cpHelpers.toggleMenuItemOption(graph.el, 'Date Filter', GENERATOR_INDEXES[otherId]);
                }
                const itemIndex = COMPARISON_OPTION_INDEXES[comparisonOptionId];
                await cpHelpers.toggleComparisonMenu(graph.el);
                await cpHelpers.toggleMenuItem(graph.el, itemIndex);
            };

            // groupby menu is assumed to be closed
            this.selectDateIntervalOption = async (intervalOption) => {
                await cpHelpers.toggleGroupByMenu(graph.el);
                const productWasSelected = cpHelpers.isItemSelected(graph.el, 'Product');

                const facetEls = graph.el.querySelectorAll('.o_searchview_facet');
                const facetIndex = [...facetEls].findIndex(el => !!el.querySelector('span.fa-bars'));
                if (facetIndex > -1) {
                    await cpHelpers.removeFacet(graph.el, facetIndex);
                    await cpHelpers.toggleGroupByMenu(graph.el);
                }

                if (productWasSelected && !this.keepDateFirst) {
                    await cpHelpers.toggleMenuItem(graph.el, 'Product');
                }

                const optionIndex = INTERVAL_OPTION_IDS.indexOf(intervalOption);
                await cpHelpers.toggleMenuItem(graph.el, 'Date');
                await cpHelpers.toggleMenuItemOption(graph.el, 'Date', optionIndex);

                if (productWasSelected && this.keepDateFirst) {
                    await cpHelpers.toggleMenuItem(graph.el, 'Product');
                }
                await cpHelpers.toggleGroupByMenu(graph.el);
            };

            // groupby menu is assumed to be closed
            this.selectGroupBy = async (groupByName) => {
                await cpHelpers.toggleGroupByMenu(graph.el);
                if (!cpHelpers.isItemSelected(graph.el, groupByName)) {
                    await cpHelpers.toggleMenuItem(graph.el, groupByName);
                }
                await cpHelpers.toggleGroupByMenu(graph.el);
            };

            this.setConfig = async (combination) => {
                await this.selectTimeRanges(combination[0], combination[1]);
                if (combination.length === 3) {
                    await this.selectDateIntervalOption(combination[2]);
                }
            };

            this.setMode = async (mode) => {
                await testUtils.dom.click($(`.o_control_panel .o_graph_button[data-mode="${mode}"]`));
            };

        },
        afterEach: function () {
            this.unpatchDate();
            this.graph.destroy();
        },
    }, function () {
        QUnit.test('comparison with one groupby equal to comparison date field', async function (assert) {
            assert.expect(11);

            this.combinationsToCheck = {
                'previous_period,this_year__this_month,day': {
                    labels: [...Array(6).keys()].map(x => [x]),
                    legend: ["December 2016", "November 2016"],
                    datasets: [
                        {
                            data: [110, 48, 26, 53, 63, 4],
                            label: "December 2016",
                        },
                        {
                            data: [53, 24, 2, 48],
                            label: "November 2016",
                        }
                    ],
                }
            };

            const combinations = COMBINATIONS_WITH_DATE;
            await this.testCombinations(combinations, assert);
            await this.setMode('line');
            await this.testCombinations(combinations, assert);
            this.combinationsToCheck['previous_period,this_year__this_month,day'] = {
                labels: [...Array(6).keys()].map(x => [x]),
                legend: [
                    "2016-12-01,2016-11-01",
                    "2016-12-10,2016-11-03",
                    "2016-12-15,2016-11-22",
                    "2016-12-17,2016-11-30",
                    "2016-12-19",
                    "2016-12-20"
                ],
                datasets: [
                    {
                        data: [110, 48, 26, 53, 63, 4],
                        label: "December 2016",
                    },
                    {
                        data: [53, 24, 2, 48, 0, 0],
                        label: "November 2016",
                    }
                ],
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            // isNotVisible can not have two elements so checking visibility of first element
            assert.isNotVisible(this.graph.$('button[data-order]:first'),
                "there should not be order button in comparison mode");
            assert.ok(true, "No combination causes a crash");
        });

        QUnit.test('comparison with no groupby', async function (assert) {
            assert.expect(10);

            this.combinationsToCheck = {
                'previous_period,this_year__this_month': {
                    labels: [[]],
                    legend: ["December 2016", "November 2016"],
                    datasets: [
                        {
                            data: [304],
                            label: "December 2016",
                        },
                        {
                            data: [127],
                            label: "November 2016",
                        }
                    ],
                }
            };

            const combinations = COMBINATIONS;
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_period,this_year__this_month'] = {
                labels: [[''], [], ['']],
                legend: ["December 2016", "November 2016"],
                datasets: [
                    {
                        data: [undefined, 304],
                        label: "December 2016",
                    },
                    {
                        data: [undefined, 127],
                        label: "November 2016",
                    }
                ],
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_period,this_year__this_month'] = {
                labels: [[]],
                legend: ["Total"],
                datasets: [
                    {
                        data: [304],
                        label: "December 2016",
                    },
                    {
                        data: [127],
                        label: "November 2016",
                    }
                ],
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");
        });

        QUnit.test('comparison with one groupby different from comparison date field', async function (assert) {
            assert.expect(10);

            this.combinationsToCheck = {
                'previous_period,this_year__this_month': {
                    labels: [["xpad"], ["xphone"], ["Undefined"]],
                    legend: ["December 2016", "November 2016"],
                    datasets: [
                        {
                            data: [155, 149, 0],
                            label: "December 2016",
                        },
                        {
                            data: [53, 26, 48],
                            label: "November 2016",
                        }
                    ],
                }
            };

            const combinations = COMBINATIONS;
            await this.selectGroupBy('Product');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_period,this_year__this_month'] = {
                labels: [["xpad"], ["xphone"]],
                legend: ["December 2016", "November 2016"],
                datasets: [
                    {
                        data: [155, 149],
                        label: "December 2016",
                    },
                    {
                        data: [53, 26],
                        label: "November 2016",
                    }
                ],
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_period,this_year__this_month'] = {
                labels: [["xpad"], ["xphone"], ["Undefined"]],
                legend: ["xpad", "xphone", "Undefined"],
                datasets: [
                    {
                        data: [155, 149, 0],
                        label: "December 2016",
                    },
                    {
                        data: [53, 26, 48],
                        label: "November 2016",
                    }
                ],
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");
        });

        QUnit.test('comparison with two groupby with first groupby equal to comparison date field', async function (assert) {
            assert.expect(10);

            this.keepDateFirst = true;
            this.combinationsToCheck = {
                'previous_period,this_year__this_month,day': {
                    labels: [...Array(6).keys()].map(x => [x]),
                    legend: [
                        "December 2016/xpad",
                        "December 2016/xphone",
                        "November 2016/xpad",
                        "November 2016/xphone",
                        "November 2016/Undefined"
                    ],
                    datasets: [
                        {
                            data: [65, 0, 23, 0, 63, 4],
                            label: "December 2016/xpad"
                        },
                        {
                            data: [45, 48, 3, 53, 0, 0],
                            label: "December 2016/xphone"
                        },
                        {
                            data: [53, 0, 0, 0],
                            label: "November 2016/xpad"
                        },
                        {
                            data: [0, 24, 2, 0],
                            label: "November 2016/xphone"
                        },
                        {
                            data: [0, 0, 0, 48],
                            label: "November 2016/Undefined"
                        }
                    ]
                }
            };

            const combinations = COMBINATIONS_WITH_DATE;
            await this.selectGroupBy('Product');
            await this.testCombinations(combinations, assert);
            await this.setMode('line');
            await this.testCombinations(combinations, assert);


            this.combinationsToCheck['previous_period,this_year__this_month,day'] = {
                labels: [[0, "xpad"], [0, "xphone"], [1, "xphone"], [2, "xphone"], [2, "xpad"], [3, "xphone"], [4, "xpad"], [5, "xpad"], [3, "Undefined"]],
                legend: [
                    "2016-12-01,2016-11-01/xpad",
                    "2016-12-01,2016-11-01/xphone",
                    "2016-12-10,2016-11-03/xphone",
                    "2016-12-15,2016-11-22/xphone",
                    "2016-12-15,2016-11-22/xpad",
                    "2016-12-17,2016-11-30/xphone",
                    "2016-12-19/xpad",
                    "2016-12-20/xpad",
                    "2016-12-17,2016-11-30/Undefine..."
                ],
                datasets: [
                    {
                        "data": [65, 45, 48, 3, 23, 53, 63, 4, 0],
                        "label": "December 2016"
                    },
                    {
                        "data": [53, 0, 24, 2, 0, 0, 0, 0, 48],
                        "label": "November 2016"
                    }
                ],
            };

            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");

            this.keepDateFirst = false;
        });

        QUnit.test('comparison with two groupby with second groupby equal to comparison date field', async function (assert) {
            assert.expect(8);

            this.combinationsToCheck = {
                'previous_period,this_year,quarter': {
                    labels: [["xphone"], ["xpad"], ["Undefined"]],
                    legend: [
                        "2016/Q3 2016",
                        "2016/Q4 2016",
                        "2015/Q2 2015"
                    ],
                    datasets: [
                        {
                            data: [-156, 48, 53],
                            label: "2016/Q3 2016",
                        },
                        {
                            data: [175, 208, 48],
                            label: "2016/Q4 2016",
                        },
                        {
                            data: [0, 109, 0],
                            label: "2015/Q2 2015",
                        },
                    ]
                }
            };

            const combinations = COMBINATIONS_WITH_DATE;
            await this.selectGroupBy('Product');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_period,this_year,quarter'] = {
                labels: [["xphone"], ["xpad"]],
                legend: [
                    "2016/Q3 2016",
                    "2016/Q4 2016",
                    "2015/Q2 2015"
                ],
                datasets: [
                    {
                        data: [-156, 48],
                        label: "2016/Q3 2016",
                    },
                    {
                        data: [175, 208],
                        label: "2016/Q4 2016",
                    },
                    {
                        data: [0, 109],
                        label: "2015/Q2 2015",
                    },
                ]
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_period,this_year,quarter'] = {
                errorMessage: 'Pie chart cannot mix positive and negative numbers. ' +
                    'Try to change your domain to only display positive results'
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");
        });
        QUnit.test('comparison with two groupby with no groupby equal to comparison date field', async function (assert) {
            assert.expect(10);

            this.combinationsToCheck = {
                'previous_year,this_year__last_month': {
                    labels: [["xpad"], ["xphone"], ["Undefined"]],
                    legend: ["November 2016/false", "November 2016/true"],
                    datasets: [
                        {
                            data: [53, 24, 48],
                            label: "November 2016/false",
                        },
                        {
                            data: [0, 2, 0],
                            label: "November 2016/true",
                        }
                    ],
                }
            };

            const combinations = COMBINATIONS;
            await this.selectGroupBy('Product');
            await this.selectGroupBy('Bar');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_year,this_year__last_month'] = {
                labels: [["xpad"], ["xphone"]],
                legend: ["November 2016/false", "November 2016/true"],
                datasets: [
                    {
                        data: [53, 24],
                        label: "November 2016/false",
                    },
                    {
                        data: [0, 2],
                        label: "November 2016/true",
                    }
                ],
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['previous_year,this_year__last_month'] = {
                labels:
                    [["xpad", false], ["xphone", false], ["xphone", true], ["Undefined", false], ["No data"]],
                legend: [
                    "xpad/false",
                    "xphone/false",
                    "xphone/true",
                    "Undefined/false",
                    "No data"
                ],
                datasets: [
                    {
                        "data": [53, 24, 2, 48],
                        "label": "November 2016"
                    },
                    {
                        "data": [undefined, undefined, undefined, undefined, 1],
                        "label": "November 2015"
                    }
                ],
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");
        });
    });
});
});

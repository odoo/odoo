odoo.define('web.graph_view_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var GraphView = require('web.GraphView');
var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;
var createView = testUtils.createView;
var patchDate = testUtils.mock.patchDate;

var INTERVAL_OPTIONS = controlPanelViewParameters.INTERVAL_OPTIONS.map(o => o.optionId);
var TIME_RANGE_OPTIONS = controlPanelViewParameters.TIME_RANGE_OPTIONS.map(o => o.optionId);
var COMPARISON_TIME_RANGE_OPTIONS = controlPanelViewParameters.COMPARISON_TIME_RANGE_OPTIONS.map(o => o.optionId);

var f = (a, b) => [].concat(...a.map(d => b.map(e => [].concat(d, e))));
var cartesian = (a, b, ...c) => (b ? cartesian(f(a, b), ...c) : a);

var COMBINATIONS = cartesian(TIME_RANGE_OPTIONS, COMPARISON_TIME_RANGE_OPTIONS);
var COMBINATIONS_WITH_DATE = cartesian(TIME_RANGE_OPTIONS, COMPARISON_TIME_RANGE_OPTIONS, INTERVAL_OPTIONS);

QUnit.assert.checkDatasets = function (graph, keys, expectedDatasets) {
    keys = keys instanceof Array ? keys : [keys];
    expectedDatasets = expectedDatasets instanceof Array ?
                            expectedDatasets :
                            [expectedDatasets];
    var datasets = graph.renderer.chart.data.datasets;
    var actualValues = datasets.map(dataset => _.pick(dataset, keys));
    this.pushResult({
        result: _.isEqual(actualValues, expectedDatasets),
        actual: actualValues,
        expected: expectedDatasets,
    });
};

QUnit.assert.checkLabels = function (graph, expectedLabels) {
    var labels = graph.renderer.chart.data.labels;
    this.pushResult({
        result: _.isEqual(labels, expectedLabels),
        actual: labels,
        expected: expectedLabels,
    });
};

QUnit.assert.checkLegend = function (graph, expectedLegendLabels) {
    expectedLegendLabels = expectedLegendLabels instanceof Array ?
                                expectedLegendLabels :
                                [expectedLegendLabels];
    var chart = graph.renderer.chart;
    var actualLegendLabels = chart.config.options.legend.labels.generateLabels(chart).map(o => o.text);

    this.pushResult({
        result: _.isEqual(actualLegendLabels, expectedLegendLabels),
        actual: actualLegendLabels,
        expected: expectedLegendLabels,
    });
};

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "integer", store: true},
                    bar: {string: "bar", type: "boolean"},
                    product_id: {string: "Product", type: "many2one", relation: 'product', store: true},
                    color_id: {string: "Color", type: "many2one", relation: 'color'},
                    date: {string: "Date", type: 'date', store: true, sortable: true},
                },
                records: [
                    {id: 1, foo: 3, bar: true, product_id: 37, date: "2016-01-01"},
                    {id: 2, foo: 53, bar: true, product_id: 37, color_id: 7, date: "2016-01-03"},
                    {id: 3, foo: 2, bar: true, product_id: 37, date: "2016-03-04"},
                    {id: 4, foo: 24, bar: false, product_id: 37, date: "2016-03-07"},
                    {id: 5, foo: 4, bar: false, product_id: 41, date: "2016-05-01"},
                    {id: 6, foo: 63, bar: false, product_id: 41},
                    {id: 7, foo: 42, bar: false, product_id: 41},
                    {id: 8, foo: 48, bar: false, product_id: 41, date: "2016-04-01"},
                ]
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"}
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
                    name: {string: "Color", type: "char"}
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
    }
}, function () {

    QUnit.module('GraphView');

    QUnit.test('simple graph rendering', async function (assert) {
        assert.expect(5);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
                    "should contain a div with a canvas element");
        assert.strictEqual(graph.renderer.state.mode, "bar",
            "should be in bar chart mode by default");
        assert.checkLabels(graph, [[true], [false]]);
        assert.checkDatasets(graph,
            ['backgroundColor', 'data', 'label', 'originIndex', 'stack'],
            {
                backgroundColor: "#1f77b4",
                data: [3,5],
                label: "Count",
                originIndex: 0,
                stack: "",
            }
        );
        assert.checkLegend(graph, 'Count');

        graph.destroy();
    });

    QUnit.test('default type attribute', async function (assert) {
        assert.expect(1);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="pie">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        assert.strictEqual(graph.renderer.state.mode, "pie", "should be in pie chart mode by default");

        graph.destroy();
    });

    QUnit.test('title attribute', async function (assert) {
        assert.expect(1);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph title="Partners" type="pie">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        assert.strictEqual(graph.$('.o_graph_renderer label').text(), "Partners",
            "should have 'Partners as title'");

        graph.destroy();
    });

    QUnit.test('field id not in groupBy', async function (assert) {
        assert.expect(1);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="id"/>' +
                '</graph>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.groupby, [],
                        'groupby should not contain id field');
                }
                return this._super.apply(this, arguments);
            }
        });
        graph.destroy();
    });

    QUnit.test('switching mode', async function (assert) {
        assert.expect(6);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="line">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        assert.strictEqual(graph.renderer.state.mode, "line", "should be in line chart mode by default");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar type button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="line"]'),'active',
            'line type button should be active');

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="bar"]'));
        assert.strictEqual(graph.renderer.state.mode, "bar", "should be in bar chart mode by default");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="line"]'), 'active',
            'line type button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="bar"]'),'active',
            'bar type button should be active');

        graph.destroy();
    });

    QUnit.test('displaying line chart with only 1 data point', async function (assert) {
        assert.expect(1);
         // this test makes sure the line chart does not crash when only one data
        // point is displayed.
        this.data.foo.records = this.data.foo.records.slice(0,1);
        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="line">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        assert.containsOnce(graph, 'canvas', "should have a canvas");

        graph.destroy();
    });

    QUnit.test('displaying chart data with multiple groupbys', async function (assert) {
        // this test makes sure the line chart shows all data labels (X axis) when
        // it is grouped by several fields
        assert.expect(6);

        var graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: '<graph type="bar"><field name="foo" /></graph>',
            groupBy: ['product_id', 'bar', 'color_id'],
        });

        assert.checkLabels(graph, [['xphone'], ['xpad']]);
        assert.checkLegend(graph, ['true/Undefined', 'true/red', 'false/Undefined']);

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="line"]'));
        assert.checkLabels(graph, [['xphone'], ['xpad']]);
        assert.checkLegend(graph, ['true/Undefined', 'true/red', 'false/Undefined']);

        await testUtils.dom.click(graph.$buttons.find('button[data-mode="pie"]'));
        assert.checkLabels(graph, [
            ["xphone", true, "Undefined"],
            ["xphone", true,"red"],
            ["xphone", false, "Undefined"],
            ["xpad", false, "Undefined"]
        ]);
        assert.checkLegend(graph, [
            'xphone/true/Undefined',
            'xphone/true/red',
            'xphone/false/Undefined',
            'xpad/false/Undefined'
        ]);

        graph.destroy();
    });

    QUnit.test('switching measures', async function (assert) {
        assert.expect(2);

        var rpcCount = 0;

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
            mockRPC: function (route, args) {
                rpcCount++;
                return this._super(route, args);
            },
        });

        testUtils.dom.click(graph.$buttons.find('.dropdown-toggle:contains(Measures)'));
        await testUtils.dom.click(graph.$buttons.find('.dropdown-item[data-field="foo"]'));
        assert.checkLegend(graph, 'Foo');
        assert.strictEqual(rpcCount, 2, "should have done 2 rpcs (2 readgroups)");

        graph.destroy();
    });

    QUnit.test('no content helper (bar chart)', async function (assert) {
        assert.expect(2);
        this.data.foo.records = [];

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });

        assert.containsNone(graph, 'div.o_graph_canvas_container canvas',
                    "should not contain a div with a canvas element");
        assert.containsOnce(graph, 'div.o_view_nocontent',
            "should display the no content helper");

        graph.destroy();
    });

    QUnit.test('no content helper (pie chart)', async function (assert) {
        assert.expect(2);
        this.data.foo.records =  []

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph type="pie">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });

        assert.containsNone(graph, 'div.o_graph_canvas_container canvas',
            "should not contain a div with a canvas element");
        assert.containsOnce(graph, 'div.o_view_nocontent',
            "should display the no content helper");

        graph.destroy();
    });

    QUnit.test('render pie chart in comparison mode', async function (assert) {
        assert.expect(2);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            context: {
                timeRangeMenuData: {
                    //Q3 2018
                    timeRange: ['&', ["date", ">=", "2018-07-01"],["date", "<=", "2018-09-30"]],
                    timeRangeDescription: 'This Quarter',
                    //Q4 2018
                    comparisonTimeRange: ['&', ["date", ">=", "2018-10-01"],["date", "<=", "2018-12-31"]],
                    comparisonTimeRangeDescription: 'Previous Period',
                },
            },
            arch: '<graph type="pie">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });

        assert.containsNone(graph, 'div.o_view_nocontent',
        "should not display the no content helper");
        assert.checkLegend(graph, 'No data');

        graph.destroy();
    });

    QUnit.test('no content helper after update', async function (assert) {
        assert.expect(4);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });

        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
                    "should contain a div with a canvas element");
        assert.containsNone(graph, 'div.o_view_nocontent',
            "should not display the no content helper");

        await testUtils.graph.reload(graph, {domain: [['product_id', '=', 4]]});
        assert.containsNone(graph, 'div.o_graph_canvas_container canvas',
                    "should not contain a div with a canvas element");
        assert.containsOnce(graph, 'div.o_view_nocontent',
            "should display the no content helper");
        graph.destroy();
    });

    QUnit.test('can reload with other group by', async function (assert) {
        assert.expect(2);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });

        assert.checkLabels(graph, [['xphone'], ['xpad']]);

        await testUtils.graph.reload(graph, {groupBy: ['color_id']});
        assert.checkLabels(graph, [['Undefined'], ['red']]);

        graph.destroy();
    });

    QUnit.test('getOwnedQueryParams correctly returns mode, measure, and groupbys', async function (assert) {
        assert.expect(4);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });

        assert.deepEqual(graph.getOwnedQueryParams(), {
            context: {
                graph_mode: 'bar',
                graph_measure: '__count__',
                graph_groupbys: ['product_id'],
            }
        }, "context should be correct");

        testUtils.dom.click(graph.$buttons.find('.dropdown-toggle:contains(Measures)'));
        await testUtils.dom.click(graph.$buttons.find('.dropdown-item[data-field="foo"]'));
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

        await testUtils.graph.reload(graph, {groupBy: ['product_id', 'color_id']}); // change groupbys
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

        var lastOne = _.last(this.data.foo.records);
        lastOne.color_id = 14;

        var graph = await createView({
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
        assert.checkLegend(graph, 'Foo');
        // check mode
        assert.strictEqual(graph.renderer.state.mode, "line", "should be in line chart mode");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar chart button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="line"]'),'active',
            'line chart button should be active');
        // check groupby values ('Undefined' is rejected in line chart) are in labels
        assert.checkLabels(graph, [['red'], ['black']]);

        graph.destroy();
    });

    QUnit.test('correctly use group_by key from the context', async function (assert) {
        assert.expect(1);

        var lastOne = _.last(this.data.foo.records);
        lastOne.color_id = 14;

        var graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: '<graph><field name="product_id" /></graph>',
            groupBy: ['color_id'],
            viewOptions: {
                context: {
                    graph_measure: 'foo',
                    graph_mode: 'line',
                },
            },
        });
        // check groupby values ('Undefined' is rejected in line chart) are in labels
        assert.checkLabels(graph, [['red'], ['black']]);

        graph.destroy();
    });

    QUnit.test('correctly uses graph_ keys from the context (at reload)', async function (assert) {
        assert.expect(7);

        var lastOne = _.last(this.data.foo.records);
        lastOne.color_id = 14;

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
        });

        assert.strictEqual(graph.renderer.state.mode, "bar", "should be in bar chart mode");
        assert.hasClass(graph.$buttons.find('button[data-mode="bar"]'),'active',
            'bar chart button should be active');

        var reloadParams = {
            context: {
                graph_measure: 'foo',
                graph_mode: 'line',
                graph_groupbys: ['color_id'],
            },
        };
        await testUtils.graph.reload(graph, reloadParams);

        // check measure
        assert.checkLegend(graph, 'Foo');
        // check mode
        assert.strictEqual(graph.renderer.state.mode, "line", "should be in line chart mode");
        assert.doesNotHaveClass(graph.$buttons.find('button[data-mode="bar"]'), 'active',
            'bar chart button should not be active');
        assert.hasClass(graph.$buttons.find('button[data-mode="line"]'),'active',
            'line chart button should be active');
        // check groupby values ('Undefined' is rejected in line chart) are in labels
        assert.checkLabels(graph, [['red'], ['black']])

        graph.destroy();
    });

    QUnit.test('reload graph with correct fields', async function (assert) {
        assert.expect(2);

        var graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: '<graph>' +
                    '<field name="product_id" type="row"/>' +
                    '<field name="foo" type="measure"/>' +
                '</graph>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.fields, ['product_id', 'foo'],
                        "should read the correct fields");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.graph.reload(graph, {groupBy: []});

        graph.destroy();
    });

    QUnit.test('initial groupby is kept when reloading', async function (assert) {
        assert.expect(8);

        var graph = await createView({
            View: GraphView,
            model: 'foo',
            data: this.data,
            arch: '<graph>' +
                    '<field name="product_id" type="row"/>' +
                    '<field name="foo" type="measure"/>' +
                '</graph>',
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    assert.deepEqual(args.kwargs.groupby, ['product_id'],
                        "should group by the correct field");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.checkLabels(graph, [['xphone'], ['xpad']]);
        assert.checkLegend(graph, 'Foo');
        assert.checkDatasets(graph, 'data', {data: [82, 157]});

        await testUtils.graph.reload(graph, {groupBy: []});
        assert.checkLabels(graph, [['xphone'], ['xpad']]);
        assert.checkLegend(graph, 'Foo');
        assert.checkDatasets(graph, 'data', {data: [82, 157]});

        graph.destroy();
    });

    QUnit.test('use a many2one as a measure should work (without groupBy)', async function (assert) {
        assert.expect(4);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="product_id" type="measure"/>' +
                '</graph>',
        });
        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
                    "should contain a div with a canvas element");
        assert.checkLabels(graph, [[]]);
        assert.checkLegend(graph, 'Product');
        assert.checkDatasets(graph, 'data', {data: [2]});

        graph.destroy();
    });

    QUnit.test('use a many2one as a measure should work (with groupBy)', async function (assert) {
        assert.expect(5);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="bar" type="row"/>' +
                        '<field name="product_id" type="measure"/>' +
                '</graph>',
        });
        assert.containsOnce(graph, 'div.o_graph_canvas_container canvas',
                    "should contain a div with a canvas element");

        assert.strictEqual(graph.renderer.state.mode, "bar",
            "should be in bar chart mode by default");
        assert.checkLabels(graph, [[true], [false]]);
        assert.checkLegend(graph, 'Product');
        assert.checkDatasets(graph, 'data', {data: [1, 2]});

        graph.destroy();
    });

    QUnit.test('use a many2one as a measure and as a groupby should work', async function (assert) {
        assert.expect(3);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="product_id" type="row"/>' +
                '</graph>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });
        // need to set the measure this way because it cannot be set in the
        // arch.
        await testUtils.dom.click(graph.$buttons.find('.dropdown-toggle:contains(Measures)'));
        await testUtils.dom.click(graph.$buttons.find('.dropdown-item[data-field="product_id"]'));

        assert.checkLabels(graph, [['xphone'], ['xpad']]);
        assert.checkLegend(graph, 'Product');
        assert.checkDatasets(graph, 'data', {data: [1, 1]});

        graph.destroy();
    });

    QUnit.test('not use a many2one as a measure by default', async function (assert) {
        assert.expect(1);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });
        assert.notOk(graph.measures.product_id,
            "should not have product_id as measure");
        graph.destroy();
    });

    QUnit.test('use a many2one as a measure if set as additional fields', async function (assert) {
        assert.expect(1);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="product_id"/>' +
                '</graph>',
            viewOptions: {
                additionalMeasures: ['product_id'],
            },
        });
        assert.ok(graph.measures.product_id,
            "should have product_id as measure");
        graph.destroy();
    });

    QUnit.test('graph view crash when moving from search view using Down key', async function (assert) {
        assert.expect(1);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="pie">' +
                        '<field name="bar"/>' +
                '</graph>',
        });
        graph.renderer.giveFocus();
        assert.ok(true,"should not generate any error");
        graph.destroy();
    });

    QUnit.test('graph measures should be alphabetically sorted', async function (assert) {
        assert.expect(2);

        var data = this.data;
        data.foo.fields.bouh = {string: "bouh", type: "integer"};

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: data,
            arch: '<graph string="Partners">' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="bouh" type="measure"/>' +
                  '</graph>',
        });

        assert.strictEqual(graph.$buttons.find('.o_graph_measures_list .dropdown-item:first').data('field'), 'bouh',
            "Bouh should be the first measure");
        assert.strictEqual(graph.$buttons.find('.o_graph_measures_list .dropdown-item:last').data('field'), '__count__',
            "Count should be the last measure");

        graph.destroy();
    });

    QUnit.test('Undefined should appear in bar, pie graph but not in line graph', async function (assert) {
        assert.expect(3);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            groupBy:['date'],
            data: this.data,
            arch: '<graph string="Partners" type="line">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        function _indexOf (label) {
            return graph.renderer._indexOf(graph.renderer.chart.data.labels, label)
        }

        assert.strictEqual(_indexOf(['Undefined']), -1);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=bar]'));
        assert.ok(_indexOf(['Undefined']) >= 0);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=pie]'));
        assert.ok(_indexOf(['Undefined']) >= 0);

        graph.destroy();
    });

    QUnit.test('Undefined should appear in bar, pie graph but not in line graph with multiple groupbys', async function (assert) {
        assert.expect(4);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            groupBy:['date', 'color_id'],
            data: this.data,
            arch: '<graph string="Partners" type="line">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        function _indexOf (label) {
            return graph.renderer._indexOf(graph.renderer.chart.data.labels, label)
        }

        assert.strictEqual(_indexOf(['Undefined']), -1);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=bar]'));
        assert.ok(_indexOf(['Undefined']) >= 0);

        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=pie]'));
        var labels = graph.renderer.chart.data.labels
        assert.ok(labels.filter(label => /Undefined/.test(label.join(''))).length >= 1);

        // Undefined should not appear after switching back to line chart
        await testUtils.dom.click(graph.$buttons.find('.o_graph_button[data-mode=line]'));
        assert.strictEqual(_indexOf(['Undefined']), -1);

        graph.destroy();
    });

    QUnit.test('no comparison and no groupby', async function (assert) {
        assert.expect(9);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="bar">' +
                        '<field name="foo" type="measure"/>' +
                '</graph>',
        });


        assert.checkLabels(graph, [[]]);
        assert.checkLegend(graph, 'Foo');
        assert.checkDatasets(graph, 'data', {data: [239]});

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=line]'));
        // the labels in line chart is translated in this case to avoid to have a single
        // point at the left of the screen and chart to seem empty.
        assert.checkLabels(graph, [[''], [], ['']]);
        assert.checkLegend(graph, 'Foo');
        assert.checkDatasets(graph, 'data', {data: [undefined, 239]});
        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=pie]'));
        assert.checkLabels(graph, [[]]);
        assert.checkLegend(graph, 'Total');
        assert.checkDatasets(graph, 'data', {data: [239]});

        graph.destroy();
    });

    QUnit.test('no comparison and one groupby', async function (assert) {
        assert.expect(9);

        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="bar">' +
                        '<field name="foo" type="measure"/>' +
                        '<field name="bar" type="row"/>' +
                '</graph>',
        });

        assert.checkLabels(graph, [[true], [false]]);
        assert.checkLegend(graph, 'Foo');
        assert.checkDatasets(graph, 'data', {data: [58, 181]});

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=line]'));
        assert.checkLabels(graph, [[true], [false]]);
        assert.checkLegend(graph, 'Foo');
        assert.checkDatasets(graph, 'data', {data: [58, 181]});

        await testUtils.dom.click(graph.$('.o_graph_button[data-mode=pie]'));

        assert.checkLabels(graph, [[true], [false]]);
        assert.checkLegend(graph, ['true', 'false']);
        assert.checkDatasets(graph, 'data', {data: [58, 181]});

        graph.destroy();
    });
    QUnit.test('no comparison and two groupby', async function (assert) {
        assert.expect(9);
        var graph = await createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="bar">' +
                        '<field name="foo" type="measure"/>' +
                '</graph>',
            groupBy: ['product_id', 'color_id'],
        });

        assert.checkLabels(graph, [['xphone'], ['xpad']])
        assert.checkLegend(graph, ['Undefined', 'red']);
        assert.checkDatasets(graph, ['label', 'data'], [
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
        assert.checkLabels(graph, [['xphone'], ['xpad']])
        assert.checkLegend(graph, ['Undefined', 'red']);
        assert.checkDatasets(graph, ['label', 'data'], [
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
        assert.checkLabels(graph, [['xphone', 'Undefined'], ['xphone', 'red'], ['xpad', 'Undefined']])
        assert.checkLegend(graph, ['xphone/Undefined', 'xphone/red', 'xpad/Undefined']);
        assert.checkDatasets(graph, ['label', 'data'], {
                label: '',
                data: [29, 53, 157],
        });

        graph.destroy();
    });

    QUnit.module('GraphView: comparison mode', {
        beforeEach: async function () {
            this.data.foo.records[0].date = '2016-12-15';
            this.data.foo.records[1].date = '2016-12-17';
            this.data.foo.records[2].date = '2016-11-22';
            this.data.foo.records[3].date = '2016-11-03';
            this.data.foo.records[4].date = '2016-12-20';
            this.data.foo.records[5].date = '2016-12-19';
            this.data.foo.records[6].date = '2016-12-15';
            this.data.foo.records[7].date = undefined;

            this.data.foo.records.push({id: 9, foo: 48, bar: false, product_id: 41, color_id: 7, date: "2016-12-01"});
            this.data.foo.records.push({id: 10, foo: 17, bar: true, product_id: 41, color_id: 7, date: "2016-12-01"});
            this.data.foo.records.push({id: 11, foo: 45, bar: true, product_id: 37, color_id: 14, date: "2016-12-01"});
            this.data.foo.records.push({id: 12, foo: 48, bar: false, product_id: 37, color_id: 7, date: "2016-12-10"});
            this.data.foo.records.push({id: 13, foo: 48, bar: false, product_id: undefined, color_id: 14, date: "2016-11-30"});
            this.data.foo.records.push({id: 14, foo: -50, bar: true, product_id: 41, color_id: 14, date: "2016-12-15"});
            this.data.foo.records.push({id: 15, foo: 53, bar: false, product_id: 41, color_id: 14, date: "2016-11-01"});
            this.data.foo.records.push({id: 16, foo: 53, bar: true, product_id: undefined, color_id: 7, date: "2016-09-01"});
            this.data.foo.records.push({id: 17, foo: 48, bar: false, product_id: 41, color_id: undefined, date: "2016-08-01"});
            this.data.foo.records.push({id: 18, foo: -156, bar: false, product_id: 37, color_id: undefined, date: "2016-07-15"});
            this.data.foo.records.push({id: 19, foo: 31, bar: false, product_id: 41, color_id: 14, date: "2016-12-15"});
            this.data.foo.records.push({id: 20, foo: 109, bar: true, product_id: 41, color_id: 7, date: "2015-06-01"});

            this.unpatchDate = patchDate(2016, 11, 20, 1, 0, 0);

            var checkOnlyToCheck = true;
            var exhaustiveTest = false || checkOnlyToCheck;

            var self = this;
            async function* graphGenerator(combinations) {
                var i = 0;
                while (i < combinations.length) {
                    var combination = combinations[i];
                    if (!checkOnlyToCheck || combination.toString() in self.combinationsToCheck) {
                        await self.setConfig(combination);
                    }
                    if (exhaustiveTest) {
                        i++;
                    } else {
                        i += Math.floor(1 + Math.random() * 20)
                    }
                    yield combination;
                }
            }

            this.combinationsToCheck = {};
            this.testCombinations = async function (combinations, assert) {
                for await (var combination of graphGenerator(combinations)) {
                    // we can check particular combinations here
                    if (combination.toString() in self.combinationsToCheck) {
                        var graph = self.actionManager.getCurrentController().widget;
                        if (self.combinationsToCheck[combination].errorMessage) {
                            assert.strictEqual(
                                graph.$('.o_nocontent_help p').eq(1).text().trim(),
                                self.combinationsToCheck[combination].errorMessage
                            );
                        } else {
                            assert.checkLabels(graph, self.combinationsToCheck[combination].labels)
                            assert.checkLegend(graph, self.combinationsToCheck[combination].legend);
                            assert.checkDatasets(graph, ['label', 'data'], self.combinationsToCheck[combination].datasets);
                        }
                    }
                }
            };

            // time range menu is assumed to be closed
            this.selectTimeRanges = async function (timeRangeOption, comparisonTimeRangeOption) {
                comparisonTimeRangeOption = comparisonTimeRangeOption || 'previous_period';
                // open time range menu
                await testUtils.dom.click($('.o_control_panel .o_time_range_menu_button'));
                // select range
                await testUtils.fields.editInput($('.o_control_panel .o_time_range_selector'), timeRangeOption);
                // check checkbox 'Compare To'
                if (!$('.o_control_panel .o_time_range_menu .o_comparison_checkbox').prop('checked')) {
                    await testUtils.dom.click($('.o_control_panel .o_time_range_menu .o_comparison_checkbox'));
                }
                // select 'Previous period' or 'Previous year' acording to comparisonTimeRangeOption
                await testUtils.fields.editInput($('.o_control_panel .o_comparison_time_range_selector'), comparisonTimeRangeOption);
                // Click on 'Apply' button
                await testUtils.dom.click($('.o_control_panel .o_time_range_menu .o_apply_range'));
            };

            // groupby menu is assumed to be closed
            this.selectDateIntervalOption = async function (intervalOption) {
                const self = this;
                intervalOption = intervalOption || 'month';

                // open group by menu
                await testUtils.dom.click($('.o_control_panel .o_dropdown span.fa-bars'));

                let wasSelected = false;
                if (this.keepFirst) {
                    if ($('.o_control_panel .o_group_by_menu .o_menu_item:contains(Product) a').hasClass('selected')) {
                        wasSelected = true;
                        await testUtils.dom.click($('.o_control_panel .o_group_by_menu .o_menu_item:contains(Product)'));
                    }
                }

                // open option submenu
                await testUtils.dom.click($('.o_control_panel .o_group_by_menu .o_menu_item:contains("Date")'));
                // check interval option if not already selected
                if (!$('.o_control_panel .o_group_by_menu .o_item_option[data-option_id="' + intervalOption + '"] a').hasClass('selected')) {
                    await testUtils.dom.click($('.o_control_panel .o_group_by_menu .o_item_option[data-option_id="' + intervalOption + '"]'));
                }
                await INTERVAL_OPTIONS.filter(oId => oId !== intervalOption).forEach(async function(oId) {
                    if ($('.o_control_panel .o_group_by_menu .o_item_option[data-option_id="' + oId + '"] a').hasClass('selected')) {
                        await testUtils.dom.click($('.o_control_panel .o_group_by_menu .o_item_option[data-option_id="' + oId + '"]'));
                    }
                });

                if (this.keepFirst) {
                    if (wasSelected && !$('.o_control_panel .o_group_by_menu .o_menu_item:contains(Product) a').hasClass('selected')) {
                        await testUtils.dom.click($('.o_control_panel .o_group_by_menu .o_menu_item:contains(Product)'));
                    }
                }

                // close group by menu
                await testUtils.dom.click($('.o_control_panel .o_dropdown span.fa-bars'));
            };

            // groupby menu is assumed to be closed
            this.selectGroupBy = async function (groupByName) {
                // open group by menu
                await testUtils.dom.click($('.o_control_panel .o_dropdown span.fa-bars'));
                // check groupBy if not already selected
                if (!$('.o_control_panel .o_group_by_menu .o_menu_item:contains(' + groupByName + ') a').hasClass('selected')) {
                    await testUtils.dom.click($('.o_control_panel .o_group_by_menu .o_menu_item:contains(' + groupByName + ')'));
                }
                // close group by menu
                await testUtils.dom.click($('.o_control_panel .o_dropdown span.fa-bars'));
            };
            // groupby menu is assumed to be closed
            this.unselectGroupBy = async function (groupByName) {
                // check groupBy if already selected

            };

            this.setConfig = async function (combination) {
                await this.selectTimeRanges(combination[0], combination[1]);
                if (combination.length === 3) {
                    await self.selectDateIntervalOption(combination[2]);
                }
            };

            this.setMode = async function (mode) {
                await testUtils.dom.click($('.o_control_panel .o_graph_button[data-mode=' + mode + ']'));
            };

            // // create an action manager to test the interactions with the search view
            this.actionManager = await createActionManager({
                data: this.data,
                archs: {
                    'foo,false,graph': '<graph string="Partners" type="bar">' +
                        '<field name="foo" type="measure"/>' +
                    '</graph>',
                    'foo,false,search': '<search>' +
                        '<filter name="date" string="Date" context="{\'group_by\': \'date\'}"/>' +
                        '<filter name="bar" string="Bar" context="{\'group_by\': \'bar\'}"/>' +
                        '<filter name="product_id" string="Product" context="{\'group_by\': \'product_id\'}"/>' +
                        '<filter name="color_id" string="Color" context="{\'group_by\': \'color_id\'}"/>' +
                    '</search>',
                },
            });

            await this.actionManager.doAction({
                res_model: 'foo',
                type: 'ir.actions.act_window',
                views: [[false, 'graph']],
                flags: {
                    graph: {
                        additionalMeasures: ['product_id'],
                    }
                }
            });
        },
        afterEach: function () {
            this.unpatchDate();
            this.actionManager.destroy();
        },
    }, function () {
        QUnit.test('comparison with one groupby equal to comparison date field', async function (assert) {
            assert.expect(10);

            this.combinationsToCheck = {
                'last_30_days,previous_period,day': {
                    labels: [...Array(7).keys()].map(x => [x]),
                    legend: ["Last 30 Days", "Previous Period"],
                    datasets: [
                        {
                            data: [26, 53, 2, 63, 110, 48, 48],
                            label: "Last 30 Days",
                        },
                        {
                            data: [24, 53],
                            label: "Previous Period",
                        }
                    ],
                }
            };

            var combinations = COMBINATIONS_WITH_DATE;
            await this.testCombinations(combinations, assert);
            await this.setMode('line');
            await this.testCombinations(combinations, assert);
            this.combinationsToCheck['last_30_days,previous_period,day'] = {
                labels: [...Array(7).keys()].map(x => [x]),
                legend: [
                    "2016-12-15,2016-11-03",
                    "2016-12-17,2016-11-01",
                    "2016-11-22",
                    "2016-12-19",
                    "2016-12-01",
                    "2016-12-10",
                    "2016-11-30",
                ],
                datasets: [
                    {
                        data: [26, 53, 2, 63, 110, 48, 48],
                        label: "Last 30 Days",
                    },
                    {
                        data: [24, 53, 0, 0, 0, 0, 0],
                        label: "Previous Period",
                    }
                ],
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");
        });

        QUnit.test('comparison with no groupby', async function (assert) {
            assert.expect(10);

            this.combinationsToCheck = {
                'last_30_days,previous_period': {
                    labels: [[]],
                    legend: ["Last 30 Days", "Previous Period"],
                    datasets: [
                        {
                            data: [350],
                            label: "Last 30 Days",
                        },
                        {
                            data: [77],
                            label: "Previous Period",
                        }
                    ],
                }
            };

            var combinations = COMBINATIONS;
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['last_30_days,previous_period'] = {
                labels: [[''], [], ['']],
                legend: ["Last 30 Days", "Previous Period"],
                datasets: [
                    {
                        data: [undefined, 350],
                        label: "Last 30 Days",
                    },
                    {
                        data: [undefined, 77],
                        label: "Previous Period",
                    }
                ],
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['last_30_days,previous_period'] =  {
                labels: [[]],
                legend: ["Total"],
                datasets: [
                    {
                        data: [350],
                        label: "Last 30 Days",
                    },
                    {
                        data: [77],
                        label: "Previous Period",
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
                'last_30_days,previous_period': {
                    labels: [["xphone"],["xpad"],["Undefined"]],
                    legend: ["Last 30 Days", "Previous Period"],
                    datasets: [
                        {
                            data: [151, 151, 48],
                            label: "Last 30 Days",
                        },
                        {
                            data: [24, 53, 0],
                            label: "Previous Period",
                        }
                    ],
                }
            };

            var combinations = COMBINATIONS;
            await this.selectGroupBy('Product');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['last_30_days,previous_period'] = {
                labels: [["xphone"],["xpad"]],
                legend: ["Last 30 Days", "Previous Period"],
                datasets: [
                    {
                        data: [151, 151],
                        label: "Last 30 Days",
                    },
                    {
                        data: [24, 53],
                        label: "Previous Period",
                    }
                ],
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['last_30_days,previous_period'] = {
                labels: [["xphone"],["xpad"],["Undefined"]],
                legend: ["xphone", "xpad", "Undefined"],
                datasets: [
                    {
                        data: [151, 151, 48],
                        label: "Last 30 Days",
                    },
                    {
                        data: [24, 53, 0],
                        label: "Previous Period",
                    }
                ],
            };
            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");
        });

        QUnit.test('comparison with two groupby with first groupby equal to comparison date field', async function (assert) {
            assert.expect(10);

            this.keepFirst = true;
            this.combinationsToCheck = {
                'last_7_days,previous_period,day': {
                    labels: [...Array(3).keys()].map(x => [x]),
                    legend: [
                        "Last 7 Days/xphone",
                        "Last 7 Days/xpad",
                        "Previous Period/xphone"
                    ],
                    datasets: [
                        {
                            data: [3, 53, 0],
                            label: "Last 7 Days/xphone",
                        },
                        {
                            data: [23, 0, 63],
                            label: "Last 7 Days/xpad",
                        },
                        {
                            data: [48],
                            label: "Previous Period/xphone",
                        }
                    ],
                }
            };

            var combinations = COMBINATIONS_WITH_DATE;
            await this.selectGroupBy('Product');
            await this.testCombinations(combinations, assert);
            await this.setMode('line');
            await this.testCombinations(combinations, assert);


            this.combinationsToCheck['last_7_days,previous_period,day'] = {
                labels: [[0,"xphone"], [1,"xphone"], [2, "xpad"], [0, "xpad"]],
                legend: [
                    "2016-12-15,2016-12-10/xphone",
                    "2016-12-17/xphone",
                    "2016-12-19/xpad",
                    "2016-12-15,2016-12-10/xpad"
                ],
                datasets: [
                    {
                        data: [3, 53, 63, 23],
                        label: "Last 7 Days",
                    },
                    {
                        data: [48, 0, 0, 0],
                        label: "Previous Period",
                    }
                ],
            };

            await this.setMode('pie');
            await this.testCombinations(combinations, assert);

            assert.ok(true, "No combination causes a crash");

            this.keepFirst = false;
        });

        QUnit.test('comparison with two groupby with second groupby equal to comparison date field', async function (assert) {
            assert.expect(8);

            this.combinationsToCheck = {
                'this_year,previous_period,quarter': {
                    labels: [["xphone"], ["xpad"],["Undefined"]],
                    legend: [
                        "This Year/Q4 2016",
                        "This Year/Q3 2016",
                        "Previous Period/Q2 2015"
                    ],
                    datasets: [
                        {
                            data: [175, 208, 48],
                            label: "This Year/Q4 2016",
                        },
                        {
                            data: [-156, 48, 53],
                            label: "This Year/Q3 2016",
                        },
                        {
                            data: [0, 109, 0],
                            label: "Previous Period/Q2 2015",
                        },
                    ]
                }
            };

            var combinations = COMBINATIONS_WITH_DATE;
            await this.selectGroupBy('Product');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['this_year,previous_period,quarter'] = {
                labels: [["xphone"], ["xpad"]],
                legend: [
                    "This Year/Q4 2016",
                    "This Year/Q3 2016",
                    "Previous Period/Q2 2015"
                ],
                datasets: [
                    {
                        data: [175, 208],
                        label: "This Year/Q4 2016",
                    },
                    {
                        data: [-156, 48],
                        label: "This Year/Q3 2016",
                    },
                    {
                        data: [0, 109],
                        label: "Previous Period/Q2 2015",
                    },
                ]
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['this_year,previous_period,quarter'] = {
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
                'last_month,previous_year': {
                    labels: [["xphone"],["Undefined"], ["xpad"]],
                    legend: ["Last Month/true", "Last Month/false"],
                    datasets: [
                        {
                            data: [2, 0, 0],
                            label: "Last Month/true",
                        },
                        {
                            data: [24, 48, 53],
                            label: "Last Month/false",
                        }
                    ],
                }
            };

            var combinations = COMBINATIONS;
            await this.selectGroupBy('Product');
            await this.selectGroupBy('Bar');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['last_month,previous_year'] = {
                labels: [["xphone"], ["xpad"]],
                legend: ["Last Month/true", "Last Month/false"],
                datasets: [
                    {
                        data: [2, 0],
                        label: "Last Month/true",
                    },
                    {
                        data: [24, 53],
                        label: "Last Month/false",
                    }
                ],
            };
            await this.setMode('line');
            await this.testCombinations(combinations, assert);

            this.combinationsToCheck['last_month,previous_year'] = {
                labels: [
                    ["xphone", true],
                    ["xphone", false],
                    ["Undefined", false],
                    ["xpad", false],
                    ["No data"]
                ],
                legend: [
                    "xphone/true",
                    "xphone/false",
                    "Undefined/false",
                    "xpad/false",
                    "No data"
                ],
                datasets: [
                    {
                        data: [2, 24, 48, 53],
                        label: "Last Month",
                    },
                    {
                        data: [undefined, undefined, undefined, undefined, 1],
                        label: "Previous Year",
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
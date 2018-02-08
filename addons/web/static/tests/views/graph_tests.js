odoo.define('web.graph_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var GraphView = require('web.GraphView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "integer", store: true},
                    bar: {string: "bar", type: "boolean"},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    color_id: {string: "Color", type: "many2one", relation: 'color'},
                },
                records: [
                    {id: 1, foo: 3, bar: true, product_id: 37},
                    {id: 2, foo: 53, bar: true, product_id: 37, color_id: 7},
                    {id: 3, foo: 2, bar: true, product_id: 37},
                    {id: 4, foo: 24, bar: false, product_id: 37},
                    {id: 5, foo: 4, bar: false, product_id: 41},
                    {id: 6, foo: 63, bar: false, product_id: 41},
                    {id: 7, foo: 42, bar: false, product_id: 41},
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

    QUnit.test('simple graph rendering', function (assert) {
        assert.expect(4);

        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners">' +
                        '<field name="bar"/>' +
                '</graph>',
        });

        var done = assert.async();
        return concurrency.delay(0).then(function () {
            assert.strictEqual(graph.$('div.o_graph_svg_container svg.nvd3-svg').length, 1,
                        "should contain a div with a svg element");

            assert.strictEqual(graph.renderer.state.mode, "bar",
                "should be in bar chart mode by default");

            // here, we would like to test the svg in the dom.  However, it is
            // not so easy, because there is an animation which means that we
            // don't really have a nice way to find the proper rect elements.
            // So, instead we will do some white box testing.
            assert.strictEqual(graph.model.chart.data[0].value, 3,
                "should have first datapoint with value 3");
            assert.strictEqual(graph.model.chart.data[1].value, 4,
                "should have first datapoint with value 4");
            graph.destroy();
            done();
        });
    });

    QUnit.test('default type attribute', function (assert) {
        assert.expect(1);

        var graph = createView({
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

    QUnit.test('switching mode', function (assert) {
        assert.expect(6);

        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="line">' +
                        '<field name="bar"/>' +
                '</graph>',
        });
        assert.strictEqual(graph.renderer.state.mode, "line", "should be in line chart mode by default");
        assert.notOk(graph.$buttons.find('button[data-mode="bar"]').hasClass('active'),
            'bar type button should not be active');
        assert.ok(graph.$buttons.find('button[data-mode="line"]').hasClass('active'),
            'line type button should be active');
        graph.$buttons.find('button[data-mode="bar"]').click();
        assert.strictEqual(graph.renderer.state.mode, "bar", "should be in bar chart mode by default");
        assert.notOk(graph.$buttons.find('button[data-mode="line"]').hasClass('active'),
            'line type button should not be active');
        assert.ok(graph.$buttons.find('button[data-mode="bar"]').hasClass('active'),
            'bar type button should be active');
        graph.destroy();
    });

    QUnit.test('displaying line chart with only 1 data point', function (assert) {
        assert.expect(2);

        // this test makes sure the line chart does not crash when only one data
        // point is displayed.  This was the case since a line cannot be drawn with
        // only one point of reference.
        var done = assert.async();
        this.data.foo.records = this.data.foo.records.slice(0,1);
        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Partners" type="line">' +
                        '<field name="bar"/>' +
                '</graph>',
        });
        return concurrency.delay(0).then(function () {
            assert.ok(!graph.$('svg').length, "should not have a svg");
            assert.ok(graph.$('.o_view_nocontent').length, "should have an error message");
            graph.destroy();
            done();
        });
    });

    QUnit.test('switching measures', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var rpcCount = 0;

        var graph = createView({
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
        return concurrency.delay(0).then(function () {
            assert.ok(graph.$('text.nv-legend-text:contains(Count)').length,
                "should have used the correct measure");
            assert.ok(graph.$buttons.find('li[data-field="foo"]').length,
                "should have foo in the list of measures");
            graph.$buttons.find('li[data-field="foo"] a').click();

            return concurrency.delay(0);
        }).then(function () {
            assert.ok(graph.$('text.nv-legend-text:contains(Foo)').length,
                "should now use the Foo measure");
            assert.strictEqual(rpcCount, 2, "should have done 2 rpcs (2 readgroups)");
            graph.destroy();
            done();
        });
    });

    QUnit.test('no content helper', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });
        return concurrency.delay(0).then(function () {
            assert.ok(graph.$('div.o_graph_svg_container svg.nvd3-svg').length,
                        "should contain a div with a svg element");
            assert.notOk(graph.$('div.o_view_nocontent').length,
                "should not display the no content helper");
            graph.update({domain: [['product_id', '=', 4]]});

            assert.notOk(graph.$('div.o_graph_svg_container svg.nvd3-svg').length,
                        "should not contain a div with a svg element");
            assert.ok(graph.$('div.o_view_nocontent').length,
                "should display the no content helper");
            graph.destroy();
            done();
        });
    });

    QUnit.test('can reload with other group by', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });
        return concurrency.delay(0).then(function () {
            assert.ok(graph.$('text:contains(xphone)').length,
                        "should contain a text element with product in legend");
            assert.notOk(graph.$('text:contains(red)').length,
                        "should not contain a text element with color in legend");

            graph.update({groupBy: ['color_id']});

            return concurrency.delay(0);
        }).then(function () {
            assert.notOk(graph.$('text:contains(xphone)').length,
                        "should not contain a text element with product in legend");
            assert.ok(graph.$('text:contains(red)').length,
                        "should contain a text element with color in legend");
            graph.destroy();
            done();
        });
    });

    QUnit.test('getContext correctly returns mode, measure and groupbys', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph string="Gloups">' +
                        '<field name="product_id"/>' +
                '</graph>',
        });
        return concurrency.delay(0).then(function () {
            assert.deepEqual(graph.getContext(), {
                graph_mode: 'bar',
                graph_measure: '__count__',
                graph_groupbys: ['product_id'],
            }, "context should be correct");

            graph.$buttons.find('li[data-field="foo"] a').click(); // change measure

            return concurrency.delay(0);
        }).then(function () {
            assert.deepEqual(graph.getContext(), {
                graph_mode: 'bar',
                graph_measure: 'foo',
                graph_groupbys: ['product_id'],
            }, "context should be correct");

            graph.$buttons.find('button[data-mode="line"]').click(); // change mode

            return concurrency.delay(0);
        }).then(function () {
            assert.deepEqual(graph.getContext(), {
                graph_mode: 'line',
                graph_measure: 'foo',
                graph_groupbys: ['product_id'],
            }, "context should be correct");

            graph.update({groupBy: ['product_id', 'color_id']}); // change groupbys

            return concurrency.delay(0);
        }).then(function () {
            assert.deepEqual(graph.getContext(), {
                graph_mode: 'line',
                graph_measure: 'foo',
                graph_groupbys: ['product_id', 'color_id'],
            }, "context should be correct");

            graph.destroy();
            done();
        });
    });

    QUnit.test('correctly uses graph_ keys from the context', function (assert) {
        var done = assert.async();
        assert.expect(6);

        var graph = createView({
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
        return concurrency.delay(0).then(function () {
            // check measure
            assert.strictEqual(graph.$('text.nv-legend-text:contains(Foo)').length, 1,
                "should now use the 'foo' measure");

            // check mode
            assert.strictEqual(graph.renderer.state.mode, "line", "should be in line chart mode");
            assert.notOk(graph.$buttons.find('button[data-mode="bar"]').hasClass('active'),
                'bar chart button should not be active');
            assert.ok(graph.$buttons.find('button[data-mode="line"]').hasClass('active'),
                'line chart button should be active');

            // check groupbys
            assert.strictEqual(graph.$('text:contains(xphone)').length, 0,
                        "should not contain a text element with product in legend");
            assert.strictEqual(graph.$('text:contains(red)').length, 1,
                        "should contain a text element with color in legend");

            graph.destroy();
            done();
        });
    });

    QUnit.test('correctly use group_by key from the context', function (assert) {
        var done = assert.async();
        assert.expect(2);

        var graph = createView({
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
        return concurrency.delay(0).then(function () {
            assert.strictEqual(graph.$('text:contains(xphone)').length, 0,
                        'should not contain a text element with product in legend');
            assert.strictEqual(graph.$('text:contains(red)').length, 1,
                        'should contain a text element with color in legend');
            graph.destroy();
            done();
        });
    });

    QUnit.test('correctly uses graph_ keys from the context (at reload)', function (assert) {
        var done = assert.async();
        assert.expect(8);

        var graph = createView({
            View: GraphView,
            model: "foo",
            data: this.data,
            arch: '<graph><field name="product_id"/></graph>',
        });

        assert.strictEqual(graph.renderer.state.mode, "bar", "should be in bar chart mode");
        assert.ok(graph.$buttons.find('button[data-mode="bar"]').hasClass('active'),
            'bar chart button should be active');

        var reloadParams = {
            context: {
                graph_measure: 'foo',
                graph_mode: 'line',
                graph_groupbys: ['color_id'],
            },
        };
        graph.reload(reloadParams);
        return concurrency.delay(0).then(function () {
            // check measure
            assert.strictEqual(graph.$('text.nv-legend-text:contains(Foo)').length, 1,
                "should now use the 'foo' measure");

            // check mode
            assert.strictEqual(graph.renderer.state.mode, "line", "should be in line chart mode");
            assert.notOk(graph.$buttons.find('button[data-mode="bar"]').hasClass('active'),
                'bar chart button should not be active');
            assert.ok(graph.$buttons.find('button[data-mode="line"]').hasClass('active'),
                'line chart button should be active');

            // check groupbys
            assert.strictEqual(graph.$('text:contains(xphone)').length, 0,
                        "should not contain a text element with product in legend");
            assert.strictEqual(graph.$('text:contains(red)').length, 1,
                        "should contain a text element with color in legend");

            graph.destroy();
            done();
        });
    });

    QUnit.test('reload graph with correct fields', function (assert) {
        assert.expect(2);

        var graph = createView({
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

        graph.reload({groupBy: []});

        graph.destroy();
    });

    QUnit.test('initial groupby is kept when reloading', function (assert) {
        var done = assert.async();
        assert.expect(4);

        var graph = createView({
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


        return concurrency.delay(0).then(function () {
            assert.strictEqual(graph.$('.nv-groups rect').length, 2,
                "should display two groups");

            graph.reload({groupBy: []});
            return concurrency.delay(0).then(function () {
                assert.strictEqual(graph.$('.nv-groups rect').length, 2,
                    "should still display two groups");

                graph.destroy();
                done();
            });
        });
    });
});

});

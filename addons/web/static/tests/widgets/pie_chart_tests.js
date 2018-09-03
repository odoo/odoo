odoo.define('web.pie_chart_widget_tests', function (require) {
"use strict";

var PieChart = require('web.PieChart');
var testUtils = require('web.test_utils');

function createPieChart(record, node, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var menu = new PieChart(null, record, node);
    testUtils.addMockEnvironment(menu, params);
    menu.appendTo(target);
    return menu;
}

QUnit.module('PieChartWidget', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "integer", store: true},
                    bar: {string: "bar", type: "boolean"},
                    product_id: {string: "Product", type: "many2one", relation: 'product', store: true},
                    color_id: {string: "Color", type: "many2one", relation: 'color'},
                    date: {string: "Date", type: 'date'},
                },
                records: [
                    {id: 1, foo: 3, bar: true, product_id: 37, date: "2016-01-01"},
                    {id: 2, foo: 53, bar: true, product_id: 37, color_id: 7, date: "2016-01-03"},
                    {id: 3, foo: 2, bar: true, product_id: 37, date: "2016-03-04"},
                    {id: 4, foo: 24, bar: false, product_id: 37, date: "2016-03-07"},
                    {id: 5, foo: 4, bar: false, product_id: 41, date: "2016-05-01"},
                    {id: 6, foo: 63, bar: false, product_id: 41},
                    {id: 7, foo: 42, bar: false, product_id: 41},
                ]
            },
        };
        this.record = {
            model: 'foo',
            domain: [],
            fields: {
                foo: {string: "Foo", type: "integer", store: true},
                bar: {string: "bar", type: "boolean"},
                product_id: {string: "Product", type: "many2one", relation: 'product', store: true},
                color_id: {string: "Color", type: "many2one", relation: 'color'},
                date: {string: "Date", type: 'date'},
            },
        };

        this.node = {
            attrs: {
                modifiers: {
                    title: "Bouh",
                    groupby: "bar",
                    measure: "__count",
                },
            },
        };
    },
}, function () {

    QUnit.test('use labels modifier', function (assert) {
        assert.expect(2);

        var node = this.node;
        node.attrs.modifiers.labels = 'label1,label2';

        var pieChart = createPieChart(this.record, this.node, {data: this.data});

        pieChart._render();

        assert.deepEqual(pieChart.labels, ['label1', 'label2'], 'We should use the labels defined in the modifiers');
        assert.strictEqual(pieChart.$('g .nv-legend-text').text(), 'label1label2', 'We should use the labels defined in the modifiers');

        pieChart.destroy();
    });

    QUnit.test('use domain modifier', function (assert) {
        assert.expect(2);

        var node = this.node;
        node.attrs.modifiers.domain = "[('foo', '>=', 10)]";

        var pieChart = createPieChart(this.record, this.node, {data: this.data});

        pieChart._render();

        assert.deepEqual(pieChart.domain, [['foo', '>=', 10]], 'We should have used the domain defined in the modifiers');
        assert.strictEqual(pieChart.$('.nv-label text').text(), '25%75%', 'We should have used the domain in the modifiers');

        pieChart.destroy();
    });

});
});

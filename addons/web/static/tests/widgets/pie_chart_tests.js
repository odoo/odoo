odoo.define('web.PieChart_tests', function (require) {
"use strict";

var PieChart = require('web.PieChart');
var testUtils = require('web.test_utils');

function createPieChart(record, node, params) {
    params = params || {};
    var target = params.debug ? document.body :  $('#qunit-fixture');
    var pie = new PieChart(null, record, node);
    testUtils.addMockEnvironment(pie, params);
    pie.appendTo(target);
    var model = record.model;
    var measure = node.attr.measure;
    var groupBy = node.attr.groupby;

    // ~if field in  fields... 

    debugger;
    return pie;
}

QUnit.module('widgets', {}, function () {

QUnit.module('PieChart', {
    beforeEach: function () {
        this.record = {};
        this.node = {};
    },
}, function () {
    QUnit.test('rendering a PieChart', function (assert) {
        assert.expect(0);
        var pieChart = createPieChart(this.values, null, {'debug':true});

        pieChart.destroy();
        /*
        var done = assert.async();
        assert.expect(2);

        
        */

    });
});
});
});

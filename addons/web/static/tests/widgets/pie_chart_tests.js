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
    return pie;
}

QUnit.module('widgets', {}, function () {

QUnit.module('PieChart', {
    beforeEach: function () {
        this.node = {
            attrs: {
                modifiers: {
                    title: 'Super Pie Chart',
                    measure: 'float_field',
                    groupby: 'bar',
                }
            }
        };
        this.data = {
            partner: {
                fields: {
                    date_field: {string: "Date", type: "date", store: true, sortable: true},
                    birthday: {string: "Birthday", type: "date", store: true, sortable: true},
                    foo: {string: "Foo", type: "char", store: true, sortable: true},
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                    float_field: {string: "Float", type: "float"},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop", bar: 2, date_field: "2017-01-25", birthday: "1983-07-15", float_field: 1},
                    {id: 2, display_name: "Second record", foo: "blip", bar: 1, date_field: "2017-01-24", birthday: "1982-06-04",float_field: 2},
                    {id: 3, display_name: "Third record", foo: "gnap", bar: 1, date_field: "2017-01-13", birthday: "1985-09-13",float_field: 1.618},
                    {id: 4, display_name: "Fourth record", foo: "plop", bar: 2, date_field: "2017-02-25", birthday: "1983-05-05",float_field: -1},
                    {id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, date_field: "2016-01-25", birthday: "1800-01-01",float_field: 13},
                ],
            },
        };
        this.record = {
            fields: this.data.partner.fields,
            model: 'partner',
            domain: [],
        };

    },
}, function () {

    QUnit.test('rendering a PieChart', function (assert) {

        assert.expect(0);

        // var pieChart = createPieChart(this.record, this.node, {data: this.data});

    });
});
});
});

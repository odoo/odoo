odoo.define('web.kanban_benchmarks', function (require) {
"use strict";

var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Kanban View', {
    beforeEach: function () {
        this.data = {
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "my float", type: "float"},
                },
                records: [
                    { id: 1, bar: true, foo: "yop", int_field: 10, qux: 0.4},
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13},
                ]
            },
        };
        this.arch = null;
        this.run = function (assert, done) {
            var data = this.data;
            var arch = this.arch;
            new Benchmark.Suite({})
                .add('kanban', function () {
                    var kanban = createView({
                        View: KanbanView,
                        model: 'foo',
                        data: data,
                        arch: arch,
                    });
                    kanban.destroy();
                })
                .on('cycle', function(event) {
                    assert.ok(true, String(event.target));
                })
                .on('complete', done)
                .run({ 'async': true });
        };
    }
}, function () {
    QUnit.test('simple kanban view with 2 records', function (assert) {
        var done = assert.async();
        assert.expect(1);

        this.arch = '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div>' +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo"/>' +
                '</div>' +
            '</t></templates></kanban>';

        this.run(assert, done);
    });

    QUnit.test('simple kanban view with 200 records', function (assert) {
        var done = assert.async();
        assert.expect(1);

        for (var i = 2; i < 200; i++) {
            this.data.foo.records.push({
                id: i,
                foo: "automated data" + i,
            });
        }

        this.arch = '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                '<div>' +
                '<t t-esc="record.foo.value"/>' +
                '<field name="foo"/>' +
                '</div>' +
            '</t></templates></kanban>';

        this.run(assert, done);
    });

});
});

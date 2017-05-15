odoo.define('web.list_benchmarks', function (require) {
"use strict";

var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('List View', {
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
                .add('list', function () {
                    var list = createView({
                        View: ListView,
                        model: 'foo',
                        data: data,
                        arch: arch,
                    });
                    list.destroy();
                })
                .on('cycle', function(event) {
                    assert.ok(true, String(event.target));
                })
                .on('complete', done)
                .run({ 'async': true });
        };
    }
}, function () {
    QUnit.test('simple readonly list with 2 rows and 2 fields', function (assert) {
        var done = assert.async();
        assert.expect(1);

        this.arch ='<tree><field name="foo"/><field name="int_field"/></tree>';
        this.run(assert, done);
    });

    QUnit.test('simple readonly list with 200 rows and 2 fields', function (assert) {
        var done = assert.async();
        assert.expect(1);

        for (var i = 2; i < 200; i++) {
            this.data.foo.records.push({
                id: i,
                foo: "automated data",
                int_field: 10 * i,
            });
        }
        this.arch ='<tree><field name="foo"/><field name="int_field"/></tree>';
        this.run(assert, done);
    });

    QUnit.test('simple readonly list with 200 rows and 2 fields (with widgets)', function (assert) {
        var done = assert.async();
        assert.expect(1);

        for (var i = 2; i < 200; i++) {
            this.data.foo.records.push({
                id: i,
                foo: "automated data",
                int_field: 10 * i,
            });
        }
        this.arch = '<tree><field name="foo" widget="char"/><field name="int_field" widget="integer"/></tree>';
        this.run(assert, done);
    });

    QUnit.test('simple readonly list with 200 rows 4 fields', function (assert) {
        var done = assert.async();
        assert.expect(1);

        for (var i = 2; i < 200; i++) {
            this.data.foo.records.push({
                id: i,
                foo: "automated data",
                int_field: 10 * i,
                bar: i % 2 === 0,
            });
        }
        this.arch = '<tree><field name="foo"/><field name="int_field"/><field name="bar"/><field name="qux"/></tree>';
        this.run(assert, done);
    });

});
});

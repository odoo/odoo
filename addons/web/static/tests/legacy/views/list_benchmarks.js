odoo.define('web.list_benchmarks', function (require) {
    "use strict";

    const ListView = require('web.ListView');
    const { createView } = require('web.test_utils');

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
                        {id: 1, bar: true, foo: "yop", int_field: 10, qux: 0.4},
                        {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13},
                    ]
                },
            };
            this.arch = null;
            this.run = function (assert, cb) {
                const data = this.data;
                const arch = this.arch;
                return new Promise(resolve => {
                    new Benchmark.Suite({})
                        .add('list', {
                            defer: true,
                            fn: async (deferred) => {
                                const list = await createView({
                                    View: ListView,
                                    model: 'foo',
                                    data,
                                    arch,
                                });
                                if (cb) {
                                    cb(list);
                                }
                                list.destroy();
                                deferred.resolve();
                            },
                        })
                        .on('cycle', event => {
                            assert.ok(true, String(event.target));
                        })
                        .on('complete', resolve)
                        .run({ async: true });
                });
            };
        }
    }, function () {
        QUnit.test('simple readonly list with 2 rows and 2 fields', function (assert) {
            assert.expect(1);

            this.arch = '<tree><field name="foo"/><field name="int_field"/></tree>';
            return this.run(assert);
        });

        QUnit.test('simple readonly list with 200 rows and 2 fields', function (assert) {
            assert.expect(1);

            for (let i = 2; i < 200; i++) {
                this.data.foo.records.push({
                    id: i,
                    foo: "automated data",
                    int_field: 10 * i,
                });
            }
            this.arch = '<tree><field name="foo"/><field name="int_field"/></tree>';
            return this.run(assert);
        });

        QUnit.test('simple readonly list with 200 rows and 2 fields (with widgets)', function (assert) {
            assert.expect(1);

            for (let i = 2; i < 200; i++) {
                this.data.foo.records.push({
                    id: i,
                    foo: "automated data",
                    int_field: 10 * i,
                });
            }
            this.arch = '<tree><field name="foo" widget="char"/><field name="int_field" widget="integer"/></tree>';
            return this.run(assert);
        });

        QUnit.test('editable list with 200 rows 4 fields', function (assert) {
            assert.expect(1);

            for (let i = 2; i < 200; i++) {
                this.data.foo.records.push({
                    id: i,
                    foo: "automated data",
                    int_field: 10 * i,
                    bar: i % 2 === 0,
                });
            }
            this.arch = `
                <tree editable="bottom">
                    <field name="foo" attrs="{'readonly': [['bar', '=', True]]}"/>
                    <field name="int_field"/>
                    <field name="bar"/>
                    <field name="qux"/>
                </tree>`;
            return this.run(assert, list => {
                list.$('.o_list_button_add').click();
                list.$('.o_list_button_discard').click();
            });
        });
    });
});

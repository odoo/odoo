/* global Benchmark */
odoo.define('web.kanban_benchmarks', function (require) {
    "use strict";

    const KanbanView = require('web.KanbanView');
    const { createView } = require('web.test_utils');

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
            this.run = function (assert) {
                const data = this.data;
                const arch = this.arch;
                return new Promise(resolve => {
                    new Benchmark.Suite({})
                        .add('kanban', {
                            defer: true,
                            fn: async (deferred) => {
                                const kanban = await createView({
                                    View: KanbanView,
                                    model: 'foo',
                                    data,
                                    arch,
                                });
                                kanban.destroy();
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
        QUnit.test('simple kanban view with 2 records', function (assert) {
            assert.expect(1);

            this.arch = `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <t t-esc="record.foo.value"/>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`;
            return this.run(assert);
        });

        QUnit.test('simple kanban view with 200 records', function (assert) {
            assert.expect(1);

            for (let i = 2; i < 200; i++) {
                this.data.foo.records.push({
                    id: i,
                    foo: `automated data ${i}`,
                });
            }

            this.arch = `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <t t-esc="record.foo.value"/>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`;
            return this.run(assert);
        });
    });
});

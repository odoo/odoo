/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Field } from "@web/views/fields/field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Record } from "@web/views/record";

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    click,
    editInput,
    getFixture,
    mount,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";

import { Component, xml, useState } from "@odoo/owl";

let serverData;
let target;

QUnit.module("Record Component", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            foo: "yop",
                            int_field: 10,
                            p: [],
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            foo: "blip",
                            int_field: 0,
                            p: [],
                        },
                        { id: 3, foo: "gnap", int_field: 80 },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            int_field: false,
                        },
                        { id: 5, foo: "blop", int_field: -4 },
                    ],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.test("display a simple field", async function (assert) {
        class Parent extends Component {}
        Parent.components = { Record, Field };
        Parent.template = xml`
            <Record resModel="'partner'" resId="1" fieldNames="['foo']" t-slot-scope="data">
                <span>hello</span>
                <Field name="'foo'" record="data.record"/>
            </Record>`;
        const env = await makeTestEnv({
            serverData,
            mockRPC(route) {
                assert.step(route);
            },
        });
        await mount(Parent, target, { env });
        assert.strictEqual(
            target.innerHTML,
            '<span>hello</span><div name="foo" class="o_field_widget o_field_char"><span>yop</span></div>'
        );
        assert.verifySteps([
            "/web/dataset/call_kw/partner/fields_get",
            "/web/dataset/call_kw/partner/read",
        ]);
    });

    QUnit.test("can be updated with different resId", async function (assert) {
        class Parent extends Component {
            setup() {
                this.state = useState({
                    resId: 1,
                });
            }
        }
        Parent.components = { Record, Field };
        Parent.template = xml`
            <Record resModel="'partner'" resId="state.resId" fieldNames="['foo']" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
                <button t-on-click="() => this.state.resId++">Next</button>
            </Record>`;
        const env = await makeTestEnv({
            serverData,
            mockRPC(route) {
                assert.step(route);
            },
        });
        await mount(Parent, target, { env, dev: true });
        assert.verifySteps([
            "/web/dataset/call_kw/partner/fields_get",
            "/web/dataset/call_kw/partner/read",
        ]);
        assert.containsOnce(target, ".o_field_char:contains(yop)");
        await click(target.querySelector("button"));
        assert.containsOnce(target, ".o_field_char:contains(blip)");
        assert.verifySteps(["/web/dataset/call_kw/partner/read"]);
    });

    QUnit.test("predefined fields and values", async function (assert) {
        class Parent extends Component {
            setup() {
                this.fields = {
                    foo: {
                        name: "foo",
                        type: "char",
                    },
                    bar: {
                        name: "bar",
                        type: "boolean",
                    },
                };
                this.values = {
                    foo: "abc",
                    bar: true,
                };
            }
        }
        Parent.components = { Record, Field };
        Parent.template = xml`
            <Record resModel="'partner'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        await mount(Parent, target, {
            env: await makeTestEnv({
                serverData,
                mockRPC(route) {
                    assert.step(route);
                },
            }),
        });
        assert.verifySteps([]);
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "abc");
    });

    QUnit.test("provides a way to handle changes in the record", async function (assert) {
        class Parent extends Component {
            setup() {
                this.fields = {
                    foo: {
                        name: "foo",
                        type: "char",
                    },
                    bar: {
                        name: "bar",
                        type: "boolean",
                    },
                };
                this.values = {
                    foo: "abc",
                    bar: true,
                };
            }

            onRecordChanged(record, changes) {
                assert.step("record changed");
                assert.strictEqual(record.model.constructor.name, "RelationalModel");
                assert.deepEqual(changes, { foo: "753" });
            }
        }
        Parent.components = { Record, Field };
        Parent.template = xml`
            <Record resModel="'partner'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data" onRecordChanged.bind="onRecordChanged">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        await mount(Parent, target, {
            env: await makeTestEnv({
                serverData,
                mockRPC(route) {
                    assert.step(route);
                },
            }),
        });
        assert.strictEqual(target.querySelector("[name='foo'] input").value, "abc");
        await editInput(target, "[name='foo'] input", "753");
        assert.verifySteps(["record changed"]);
        assert.strictEqual(target.querySelector("[name='foo'] input").value, "753");
    });

    QUnit.test("provides a way to handle before/after saved the record", async function (assert) {
        class Parent extends Component {
            onRecordSaved(record) {
                assert.step("onRecordSaved");
            }

            onWillSaveRecord(record) {
                assert.step("onWillSaveRecord");
            }
        }
        Parent.components = { Record, Field };
        Parent.template = xml`
            <Record resModel="'partner'" resId="1" fieldNames="['foo']" mode="'edit'" t-slot-scope="data" onRecordSaved="onRecordSaved" onWillSaveRecord="onWillSaveRecord">
                <button class="save" t-on-click="() => data.record.save()">Save</button>
                <Field name="'foo'" record="data.record"/>
            </Record>`;

        const env = await makeTestEnv({
            serverData,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        await mount(Parent, target, { env });

        await editInput(target, "[name='foo'] input", "abc");
        await click(target, "button.save");
        assert.verifySteps([
            "fields_get",
            "read",
            "onWillSaveRecord",
            "write",
            "read",
            "onRecordSaved",
        ]);
    });

    QUnit.test("handles many2one fields", async function (assert) {
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });

        serverData.models = {
            bar: {
                records: [
                    { id: 1, display_name: "bar1" },
                    { id: 3, display_name: "abc" },
                ],
            },
        };

        class Parent extends Component {
            setup() {
                this.fields = {
                    foo: {
                        name: "foo",
                        type: "many2one",
                        relation: "bar",
                    },
                };
                this.values = {
                    foo: [1, undefined],
                };
            }

            onRecordChanged(record, changes) {
                assert.step("record changed");
                assert.deepEqual(changes, { foo: 3 });
                assert.deepEqual(record.data, { foo: [3, "abc"] });
            }
        }
        Parent.components = { Record, Many2OneField };
        Parent.template = xml`
            <Record resModel="'partner'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data" onRecordChanged.bind="onRecordChanged">
                <Many2OneField name="'foo'" record="data.record" relation="'bar'" value="data.record.data.foo"/>
            </Record>
        `;

        await mount(Parent, target, {
            env: await makeTestEnv({
                serverData,
                mockRPC(route, args) {
                    assert.step(route);
                },
            }),
        });
        assert.verifySteps(["/web/dataset/call_kw/bar/read"]);
        assert.strictEqual(target.querySelector(".o_field_many2one_selection input").value, "bar1");
        await editInput(target, ".o_field_many2one_selection input", "abc");
        assert.verifySteps(["/web/dataset/call_kw/bar/name_search"]);
        await click(target.querySelectorAll(".o-autocomplete--dropdown-item a")[0]);
        assert.verifySteps(["record changed"]);
        assert.strictEqual(target.querySelector(".o_field_many2one_selection input").value, "abc");
    });

    QUnit.test(
        "supports passing dynamic values -- full control to the user of Record",
        async (assert) => {
            class Parent extends Component {
                setup() {
                    this.fields = {
                        foo: {
                            name: "foo",
                            type: "char",
                        },
                        bar: {
                            name: "bar",
                            type: "boolean",
                        },
                    };
                    this.values = owl.useState({
                        foo: "abc",
                        bar: true,
                    });
                }

                onRecordChanged(record, changes) {
                    assert.step("record changed");
                    assert.strictEqual(record.model.constructor.name, "RelationalModel");
                    assert.deepEqual(changes, { foo: "753" });
                    this.values.foo = "357";
                }
            }
            Parent.components = { Record, Field };
            Parent.template = xml`
            <Record resModel="'partner'" fieldNames="['foo']" fields="fields" values="{ foo: values.foo }" t-slot-scope="data" onRecordChanged.bind="onRecordChanged">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

            await mount(Parent, target, {
                env: await makeTestEnv({
                    serverData,
                    mockRPC(route) {
                        assert.step(route);
                    },
                }),
            });
            assert.strictEqual(target.querySelector("[name='foo'] input").value, "abc");
            await editInput(target, "[name='foo'] input", "753");
            assert.verifySteps(["record changed"]);
            await nextTick();
            assert.strictEqual(target.querySelector("[name='foo'] input").value, "357");
        }
    );

    QUnit.test("can switch records", async (assert) => {
        class Parent extends Component {
            setup() {
                this.fields = {
                    foo: {
                        name: "foo",
                        type: "char",
                    },
                    bar: {
                        name: "bar",
                        type: "boolean",
                    },
                };
                this.state = useState({ currentId: 1, num: 0 });
            }

            next() {
                this.state.currentId = 5;
                this.state.num++;
            }
        }
        Parent.components = { Record, Field };
        Parent.template = xml`
            <a id="increment" t-on-click="() => state.num++" t-esc="state.num" />
            <a id="next" t-on-click="next">NEXT</a>
            <Record resId="state.currentId" resModel="'partner'" fieldNames="['foo']" fields="fields" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        await mount(Parent, target, {
            env: await makeTestEnv({
                serverData,
                mockRPC(route, args) {
                    assert.step(`${args.method} : ${JSON.stringify(args.args)}`);
                },
            }),
        });

        assert.verifySteps([`read : [[1],["foo"]]`]);
        const increment = target.querySelector("#increment");
        const field = target.querySelector("div[name='foo']");
        assert.strictEqual(increment.textContent, "0");
        assert.strictEqual(field.textContent, "yop");

        await click(increment);
        // No reload when a render from upstream comes
        assert.verifySteps([]);
        assert.strictEqual(increment.textContent, "1");
        assert.strictEqual(field.textContent, "yop");

        await click(target.querySelector("#next"));
        assert.verifySteps([`read : [[5],["foo"]]`]);
        assert.strictEqual(increment.textContent, "2");
        assert.strictEqual(field.textContent, "blop");
    });
});

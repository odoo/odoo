/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/views/record";
import { click, getFixture, mount } from "../helpers/utils";
import { setupViewRegistries } from "../views/helpers";

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
            <Record resModel="'partner'" fieldNames="['foo']" fields="fields" initialValues="values" t-slot-scope="data">
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
});

/** @odoo-module **/

import { click, getFixture, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData, target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: { string: "Qux", type: "float", digits: [16, 1] },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "trululu",
                        },
                        turtles: {
                            string: "one2many turtle field",
                            type: "one2many",
                            relation: "turtle",
                            relation_field: "turtle_trululu",
                        },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                            string: "Color",
                        },
                        date: { string: "Some Date", type: "date" },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        user_id: { string: "User", type: "many2one", relation: "user" },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner_type", "Partner Type"],
                                ["partner", "Partner"],
                            ],
                        },
                        model_id: { string: "Model", type: "many2one", relation: "ir.model" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44,
                            p: [],
                            turtles: [2],
                            timmy: [],
                            trululu: 4,
                            user_id: 17,
                            reference: "product,37",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            product_id: 37,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                            user_id: 17,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            bar: false,
                        },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
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
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                turtle: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        turtle_foo: { string: "Foo", type: "char" },
                        turtle_bar: { string: "Bar", type: "boolean", default: true },
                        turtle_int: { string: "int", type: "integer", sortable: true },
                        turtle_description: { string: "Description", type: "text" },
                        turtle_trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                        },
                        turtle_ref: {
                            string: "Reference",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner", "Partner"],
                            ],
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            required: true,
                        },
                        partner_ids: { string: "Partner", type: "many2many", relation: "partner" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "leonardo",
                            turtle_bar: true,
                            turtle_foo: "yop",
                            partner_ids: [],
                        },
                        {
                            id: 2,
                            display_name: "donatello",
                            turtle_bar: true,
                            turtle_foo: "blip",
                            turtle_int: 9,
                            partner_ids: [2, 4],
                        },
                        {
                            id: 3,
                            display_name: "raphael",
                            product_id: 37,
                            turtle_bar: false,
                            turtle_foo: "kawa",
                            turtle_int: 21,
                            partner_ids: [],
                            turtle_ref: "product,37",
                        },
                    ],
                    onchanges: {},
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            string: "one2many partners field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Aline",
                            partner_ids: [1, 2],
                        },
                        {
                            id: 19,
                            name: "Christine",
                        },
                    ],
                },
                "ir.model": {
                    fields: {
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Partner",
                            model: "partner",
                        },
                        {
                            id: 20,
                            name: "Product",
                            model: "product",
                        },
                        {
                            id: 21,
                            name: "Partner Type",
                            model: "partner_type",
                        },
                    ],
                    onchanges: {},
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("RadioField");

    QUnit.test("fieldradio widget on a many2one in a new record", async function (assert) {
        assert.expect(6);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="product_id" widget="radio" />
                </form>
            `,
        });

        assert.ok(
            target.querySelectorAll("div.o_radio_item").length,
            "should have rendered outer div"
        );
        assert.containsN(target, "input.o_radio_input", 2, "should have 2 possible choices");
        assert.strictEqual(
            target.querySelector(".o_field_radio").textContent.replace(/\s+/g, ""),
            "xphonexpad"
        );
        assert.containsNone(target, "input:checked", "none of the input should be checked");

        await click(target.querySelectorAll("input.o_radio_input")[0]);

        assert.containsOnce(target, "input:checked", "one of the input should be checked");

        await click(target, ".o_form_button_save");

        assert.hasAttrValue(
            target.querySelector("input.o_radio_input:checked"),
            "data-value",
            "37",
            "should have saved record with correct value"
        );
    });

    QUnit.test("required fieldradio widget on a many2one", async function (assert) {
        assert.expect(4);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="product_id" widget="radio" required="1"/></form>',
        });

        assert.containsNone(
            target,
            ".o_field_radio input:checked",
            "none of the input should be checked"
        );

        await click(target, ".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o_notification_title").textContent,
            "Invalid fields: "
        );
        assert.strictEqual(
            target.querySelector(".o_notification_content").innerHTML,
            "<ul><li>Product</li></ul>"
        );
        assert.hasClass(target.querySelector(".o_notification"), "border-danger");
    });

    QUnit.test("fieldradio change value by onchange", async function (assert) {
        assert.expect(4);

        serverData.models.partner.onchanges = {
            bar(obj) {
                obj.product_id = obj.bar ? [41] : [37];
                obj.color = obj.bar ? "red" : "black";
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" />
                    <field name="product_id" widget="radio" />
                    <field name="color" widget="radio" />
                </form>
            `,
        });

        await click(target, "input[type='checkbox']");

        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='37']:checked",
            "one of the input should be checked"
        );
        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='black']:checked",
            "the other of the input should be checked"
        );

        await click(target, "input[type='checkbox']");
        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='41']:checked",
            "the other of the input should be checked"
        );
        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='red']:checked",
            "one of the input should be checked"
        );
    });

    QUnit.test("fieldradio widget on a selection in a new record", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="color" widget="radio"/>
                </form>
            `,
        });

        assert.ok(
            target.querySelectorAll("div.o_radio_item").length,
            "should have rendered outer div"
        );
        assert.containsN(target, "input.o_radio_input", 2, "should have 2 possible choices");
        assert.strictEqual(
            target.querySelector(".o_field_radio").textContent.replace(/\s+/g, ""),
            "RedBlack"
        );

        // click on 2nd option
        await click(target.querySelectorAll("input.o_radio_input")[1]);

        await click(target, ".o_form_button_save");

        assert.hasAttrValue(
            target.querySelector("input.o_radio_input:checked"),
            "data-value",
            "black",
            "should have saved record with correct value"
        );
    });

    QUnit.test("fieldradio widget has o_horizontal or o_vertical class", async function (assert) {
        assert.expect(2);

        serverData.models.partner.fields.color2 = serverData.models.partner.fields.color;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="color" widget="radio" />
                        <field name="color2" widget="radio" options="{'horizontal': True}" />
                    </group>
                </form>
            `,
        });

        assert.containsOnce(
            target,
            ".o_field_radio > div.o_vertical",
            "should have o_vertical class"
        );
        assert.containsOnce(
            target,
            ".o_field_radio div.o_horizontal",
            "should have o_horizontal class"
        );
    });

    QUnit.test("fieldradio widget with numerical keys encoded as strings", async function (assert) {
        assert.expect(7);

        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                ["0", "Red"],
                ["1", "Black"],
            ],
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="selection" widget="radio"/>
                </form>
            `,
            mockRPC: function (route, { args, method, model }) {
                if (model === "partner" && method === "write") {
                    assert.strictEqual(args[1].selection, "1", "should write correct value");
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent.replace(/\s+/g, ""),
            "RedBlack"
        );
        assert.containsNone(target, ".o_radio_input:checked", "no value should be checked");

        await click(target, ".o_form_button_edit");

        assert.containsNone(target, ".o_radio_input:checked", "no value should be checked");

        await click(target.querySelectorAll("input.o_radio_input")[1]);

        await click(target, ".o_form_button_save");

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent.replace(/\s+/g, ""),
            "RedBlack"
        );
        assert.containsOnce(
            target,
            ".o_radio_input[data-index='1']:checked",
            "'Black' should be checked"
        );

        await click(target, ".o_form_button_edit");

        assert.containsOnce(
            target,
            ".o_radio_input[data-index='1']:checked",
            "'Black' should be checked"
        );
    });

    QUnit.test(
        "widget radio on a many2one: domain updated by an onchange",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.onchanges = {
                int_field() {},
            };

            let domain = [];
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="int_field" />
                        <field name="trululu" widget="radio" />
                    </form>
                `,
                mockRPC(route, { kwargs, method }) {
                    if (method === "onchange") {
                        domain = [["id", "in", [10]]];
                        return Promise.resolve({
                            value: {
                                trululu: false,
                            },
                            domain: {
                                trululu: domain,
                            },
                        });
                    }
                    if (method === "search_read") {
                        assert.deepEqual(kwargs.domain, domain, "sent domain should be correct");
                    }
                },
            });

            await click(target, ".o_form_button_edit");
            assert.containsN(
                target,
                ".o_field_widget[name='trululu'] .o_radio_item",
                3,
                "should be 3 radio buttons"
            );

            // trigger an onchange that will update the domain
            const input = target.querySelector(".o_field_widget[name='int_field'] input");
            input.value = "2";
            await triggerEvent(input, null, "change");
            assert.containsNone(
                target,
                ".o_field_widget[name='trululu'] .o_radio_item",
                "should be no more radio button"
            );
        }
    );
});

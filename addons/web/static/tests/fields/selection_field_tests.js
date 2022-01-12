/** @odoo-module **/

import { click, triggerEvent } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

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

        setupViewRegistries();
    });

    QUnit.module("SelectionField");

    QUnit.skip("SelectionField in a list view", async function (assert) {
        assert.expect(3);

        serverData.models.partner.records.forEach(function (r) {
            r.color = "red";
        });

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: '<tree string="Colors" editable="top">' + '<field name="color"/>' + "</tree>",
        });

        assert.strictEqual(
            list.$("td:contains(Red)").length,
            3,
            "should have 3 rows with correct value"
        );
        await testUtils.dom.click(list.$("td:contains(Red):first"));

        var $td = list.$("tbody tr.o_selected_row td:not(.o_list_record_selector)");

        assert.strictEqual($td.find("select").length, 1, "td should have a child 'select'");
        assert.strictEqual($td.contents().length, 1, "select tag should be only child of td");
        list.destroy();
    });

    QUnit.test("SelectionField, edition and on many2one field", async function (assert) {
        assert.expect(18);

        serverData.models.partner.onchanges = { product_id: function () {} };
        serverData.models.partner.records[0].product_id = 37;
        serverData.models.partner.records[0].trululu = false;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="product_id" widget="selection" />
                    <field name="trululu" widget="selection" />
                    <field name="color" widget="selection" />
                </form>
            `,
            mockRPC(route, { method }) {
                assert.step(method);
            },
        });

        assert.containsNone(form.el, "select");
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='product_id']").textContent,
            "xphone",
            "should have rendered the many2one field correctly"
        );
        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget[name='product_id'] span"),
            "raw-value",
            "37",
            "should have set the raw-value attr for many2one field correctly"
        );

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='trululu']").textContent,
            "",
            "should have rendered the unset many2one field correctly"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='color']").textContent,
            "Red",
            "should have rendered the selection field correctly"
        );
        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget[name='color'] span"),
            "raw-value",
            "red",
            "should have set the raw-value attr for selection field correctly"
        );

        await click(form.el, ".o_form_button_edit");

        assert.containsN(form.el, "select", 3);
        assert.containsOnce(
            form.el,
            ".o_field_widget[name='product_id'] select option[value='37']",
            "should have fetched xphone option"
        );
        assert.containsOnce(
            form.el,
            ".o_field_widget[name='product_id'] select option[value='41']",
            "should have fetched xpad option"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='product_id'] select").value,
            "37",
            "should have correct product_id value"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='trululu'] select").value,
            "false",
            "should not have any value in trululu field"
        );

        const select = form.el.querySelector(".o_field_widget[name='product_id'] select");
        select.value = "41";
        await triggerEvent(select, null, "change");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='product_id'] select").value,
            "41",
            "should have a value of xphone"
        );

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='color'] select").value,
            `"red"`,
            "should have correct value in color field"
        );

        assert.verifySteps(["read", "name_search", "name_search", "onchange"]);
    });

    QUnit.test("unset selection field with 0 as key", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists.
        assert.expect(2);

        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                [0, "Value O"],
                [1, "Value 1"],
            ],
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="selection" />
                </form>
            `,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "Value O",
            "the displayed value should be 'Value O'"
        );
        assert.doesNotHaveClass(
            form.el.querySelector(".o_field_widget"),
            "o_field_empty",
            "should not have class o_field_empty"
        );
    });

    QUnit.test("unset selection field with string keys", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists. In
        // this test, it doesn't exist as keys are strings.
        assert.expect(2);

        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                ["0", "Value O"],
                ["1", "Value 1"],
            ],
        };

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="selection" />
                </form>
            `,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "",
            "there should be no displayed value"
        );
        assert.hasClass(
            form.el.querySelector(".o_field_widget"),
            "o_field_empty",
            "should have class o_field_empty"
        );
    });

    QUnit.test("unset selection on a many2one field", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="trululu" widget="selection" />
                </form>
            `,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    assert.strictEqual(
                        args[1].trululu,
                        false,
                        "should send 'false' as trululu value"
                    );
                }
            },
        });

        await click(form.el, ".o_form_button_edit");

        const select = form.el.querySelector(".o_form_view select");
        select.value = "false";
        await triggerEvent(select, null, "change");

        await click(form.el, ".o_form_button_save");
    });

    QUnit.test("field selection with many2ones and special characters", async function (assert) {
        assert.expect(1);

        // edit the partner with id=4
        serverData.models.partner.records[2].display_name = "<span>hey</span>";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="trululu" widget="selection" />
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector("select option[value='4']").textContent,
            "<span>hey</span>"
        );
    });

    QUnit.test(
        "SelectionField on a many2one: domain updated by an onchange",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.onchanges = {
                int_field() {},
            };

            let domain = [];
            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="int_field" />
                        <field name="trululu" widget="selection" />
                    </form>
                `,
                mockRPC(route, { args, method }) {
                    if (method === "onchange") {
                        domain = [["id", "in", [10]]];
                        return Promise.resolve({
                            domain: {
                                trululu: domain,
                            },
                        });
                    }
                    if (method === "name_search") {
                        assert.deepEqual(args[1], domain, "sent domain should be correct");
                    }
                },
            });

            await click(form.el, ".o_form_button_edit");

            assert.containsN(
                form,
                ".o_field_widget[name='trululu'] option",
                4,
                "should be 4 options in the selection"
            );

            // trigger an onchange that will update the domain
            const input = form.el.querySelector(".o_field_widget[name='int_field'] input");
            input.value = 2;
            await triggerEvent(input, null, "change");

            assert.containsOnce(
                form,
                ".o_field_widget[name='trululu'] option",
                "should be 1 option in the selection"
            );
        }
    );

    QUnit.test("required selection widget should not have blank option", async function (assert) {
        assert.expect(3);

        serverData.models.partner.fields.feedback_value = {
            type: "selection",
            required: true,
            selection: [
                ["good", "Good"],
                ["bad", "Bad"],
            ],
            default: "good",
            string: "Good",
        };
        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="feedback_value" />
                    <field name="color" attrs="{'required': [('feedback_value', '=', 'bad')]}" />
                </form>
            `,
        });

        await click(form.el, ".o_form_button_edit");

        assert.containsN(
            form.el.querySelector(".o_field_widget[name='color']"),
            "option",
            3,
            "Three options in non required field"
        );
        assert.containsN(
            form.el.querySelector(".o_field_widget[name='feedback_value']"),
            "option",
            2,
            "Three options in required field"
        );

        // change value to update widget modifier values
        const select = form.el.querySelector(".o_field_widget[name='feedback_value'] select");
        select.value = `"bad"`;
        await triggerEvent(select, null, "change");

        assert.containsN(
            form.el.querySelector(".o_field_widget[name='color']"),
            "option",
            2,
            "Three options in non required field"
        );
    });
});

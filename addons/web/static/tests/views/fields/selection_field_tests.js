/** @odoo-module **/

import { click, editSelect, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
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
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            int_field: 10,
                            trululu: 4,
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            int_field: 9,
                            trululu: 1,
                            product_id: 37,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                        },
                    ],
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
            },
        };

        setupViewRegistries();
    });

    QUnit.module("SelectionField");

    QUnit.test("SelectionField in a list view", async function (assert) {
        serverData.models.partner.records.forEach(function (r) {
            r.color = "red";
        });

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: '<tree string="Colors" editable="top"><field name="color"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 3);
        await click(target.querySelector(".o_data_cell"));

        const td = target.querySelector("tbody tr.o_selected_row td:not(.o_list_record_selector)");
        assert.containsOnce(td, "select", "td should have a child 'select'");
        assert.strictEqual(td.children.length, 1, "select tag should be only child of td");
    });

    QUnit.test("SelectionField, edition and on many2one field", async function (assert) {
        serverData.models.partner.onchanges = { product_id: function () {} };
        serverData.models.partner.records[0].product_id = 37;
        serverData.models.partner.records[0].trululu = false;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="product_id" widget="selection" />
                    <field name="trululu" widget="selection" />
                    <field name="color" widget="selection" />
                </form>`,
            mockRPC(route, { method }) {
                assert.step(method);
            },
        });

        assert.containsNone(target, "select");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id']").textContent,
            "xphone",
            "should have rendered the many2one field correctly"
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name='product_id'] span"),
            "raw-value",
            "37",
            "should have set the raw-value attr for many2one field correctly"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='trululu']").textContent,
            "",
            "should have rendered the unset many2one field correctly"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='color']").textContent,
            "Red",
            "should have rendered the selection field correctly"
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name='color'] span"),
            "raw-value",
            "red",
            "should have set the raw-value attr for selection field correctly"
        );

        await click(target, ".o_form_button_edit");

        assert.containsN(target, "select", 3);
        assert.containsOnce(
            target,
            ".o_field_widget[name='product_id'] select option[value='37']",
            "should have fetched xphone option"
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='product_id'] select option[value='41']",
            "should have fetched xpad option"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] select").value,
            "37",
            "should have correct product_id value"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='trululu'] select").value,
            "false",
            "should not have any value in trululu field"
        );

        await editSelect(target, ".o_field_widget[name='product_id'] select", "41");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] select").value,
            "41",
            "should have a value of xphone"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='color'] select").value,
            `"red"`,
            "should have correct value in color field"
        );

        assert.verifySteps(["get_views", "read", "name_search", "name_search", "onchange"]);
    });

    QUnit.test("unset selection field with 0 as key", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists.
        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                [0, "Value O"],
                [1, "Value 1"],
            ],
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="selection" /></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "Value O",
            "the displayed value should be 'Value O'"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "should not have class o_field_empty"
        );
    });

    QUnit.test("unset selection field with string keys", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists. In
        // this test, it doesn't exist as keys are strings.
        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                ["0", "Value O"],
                ["1", "Value 1"],
            ],
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="selection" /></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "",
            "there should be no displayed value"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "should have class o_field_empty"
        );
    });

    QUnit.test("unset selection on a many2one field", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="trululu" widget="selection" /></form>',
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

        await click(target, ".o_form_button_edit");
        await editSelect(target, ".o_form_view select", "false");
        await click(target, ".o_form_button_save");
    });

    QUnit.test("field selection with many2ones and special characters", async function (assert) {
        // edit the partner with id=4
        serverData.models.partner.records[2].display_name = "<span>hey</span>";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="trululu" widget="selection" /></form>',
        });

        await click(target, ".o_form_button_edit");

        assert.strictEqual(
            target.querySelector("select option[value='4']").textContent,
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
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="int_field" />
                        <field name="trululu" widget="selection" />
                    </form>`,
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

            await click(target, ".o_form_button_edit");

            assert.containsN(
                target,
                ".o_field_widget[name='trululu'] option",
                4,
                "should be 4 options in the selection"
            );

            // trigger an onchange that will update the domain
            await editInput(target, ".o_field_widget[name='int_field'] input", 2);

            assert.containsOnce(
                target,
                ".o_field_widget[name='trululu'] option",
                "should be 1 option in the selection"
            );
        }
    );

    QUnit.test("required selection widget should not have blank option", async function (assert) {
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
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="feedback_value" />
                    <field name="color" attrs="{'required': [('feedback_value', '=', 'bad')]}" />
                </form>`,
        });

        await click(target, ".o_form_button_edit");
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                (option) => option.style.display
            ),
            ["", "", ""]
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='feedback_value'] option")].map(
                (option) => option.style.display
            ),
            ["none", "", ""]
        );

        // change value to update widget modifier values
        await editSelect(target, ".o_field_widget[name='feedback_value'] select", '"bad"');
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                (option) => option.style.display
            ),
            ["none", "", ""]
        );
    });

    QUnit.test(
        "required selection widget should have only one blank option",
        async function (assert) {
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
            serverData.models.partner.fields.color.selection = [
                [false, ""],
                ...serverData.models.partner.fields.color.selection,
            ];

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                <form>
                    <field name="feedback_value" />
                    <field name="color" attrs="{'required': [('feedback_value', '=', 'bad')]}" />
                </form>`,
            });

            await click(target, ".o_form_button_edit");
            assert.deepEqual(
                [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                    (option) => option.style.display
                ),
                ["", "", ""]
            );

            // change value to update widget modifier values
            await editSelect(target, ".o_field_widget[name='feedback_value'] select", '"bad"');
            assert.deepEqual(
                [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                    (option) => option.style.display
                ),
                ["none", "", ""]
            );
        }
    );

    QUnit.test("selection field with placeholder", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" widget="selection" placeholder="Placeholder"/>
                </form>`,
        });

        const placeholderOption = target.querySelector(
            ".o_field_widget[name='trululu'] select option"
        );
        assert.strictEqual(placeholderOption.textContent, "Placeholder");
        assert.strictEqual(placeholderOption.value, "false");
    });
});
